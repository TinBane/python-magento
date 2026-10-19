<?php
/**
 * Seed a fresh OpenMage install with what the python-magento integration
 * tests need. Runs inside the web container from /var/www/html.
 *
 * Idempotent: every block looks for its record first and only creates what is
 * missing, so it is safe to run on every bootstrap.
 *
 * Creates:
 *  - API role "pytest-all" (all resources) and API user OPENMAGE_API_USER
 *  - simple product SKU "pytest-simple" (in stock, qty topped up each run)
 *  - customer pytest.customer@example.com with a default US address
 *  - flatrate shipping + checkmo payment enabled, guest checkout allowed
 *  - store view "noemail" (same website) with new-order emails disabled
 *  - outbound mail disabled globally, system/exception logging enabled
 */

require 'app/Mage.php';

Mage::app()->setCurrentStore(Mage_Core_Model_App::ADMIN_STORE_ID);
Mage::register('isSecureArea', true);

$apiUser = getenv('OPENMAGE_API_USER') ?: 'pytest';
$apiKey  = getenv('OPENMAGE_API_KEY') ?: 'pytest-api-key-123';

function say($msg)
{
    fwrite(STDOUT, "  - {$msg}\n");
}

// --- configuration -------------------------------------------------------
$config = Mage::getConfig();
foreach ([
    'carriers/flatrate/active'        => '1',
    'carriers/flatrate/type'          => 'O',
    'carriers/flatrate/price'         => '5.00',
    'carriers/flatrate/sallowspecific' => '0',
    'payment/checkmo/active'          => '1',
    'checkout/options/guest_checkout' => '1',
    'sales_email/order/enabled'       => '1',
    'system/smtp/disable'             => '1',
    'dev/log/active'                  => '1',
    'api/config/wsdl_cache_enabled'   => '0',
] as $path => $value) {
    $config->saveConfig($path, $value, 'default', 0);
}
say('checkout/shipping/payment/email config applied');

// --- "noemail" store view ------------------------------------------------
$website = Mage::app()->getWebsite(1);
$store = Mage::getModel('core/store')->load('noemail', 'code');
if (!$store->getId()) {
    $store->setCode('noemail')
        ->setWebsiteId($website->getId())
        ->setGroupId($website->getDefaultGroupId())
        ->setName('No order email')
        ->setSortOrder(10)
        ->setIsActive(1)
        ->save();
    say("created store view noemail (id {$store->getId()})");
}
$config->saveConfig('sales_email/order/enabled', '0', 'stores', $store->getId());

$config->reinit();
Mage::app()->reinitStores();

// --- API role + user -----------------------------------------------------
$role = Mage::getModel('api/roles')->getCollection()
    ->addFieldToFilter('role_name', 'pytest-all')
    ->addFieldToFilter('role_type', 'G')
    ->getFirstItem();
if (!$role->getId()) {
    $role = Mage::getModel('api/roles')
        ->setName('pytest-all')
        ->setPid(false)
        ->setRoleType('G')
        ->save();
    say("created API role pytest-all (id {$role->getId()})");
}
Mage::getModel('api/rules')
    ->setRoleId($role->getId())
    ->setResources(['all'])
    ->saveRel();

$user = Mage::getModel('api/user')->loadByUsername($apiUser);
if (!$user->getId()) {
    $user->setData([
        'username'  => $apiUser,
        'firstname' => 'Pytest',
        'lastname'  => 'Integration',
        'email'     => $apiUser . '@example.com',
        'api_key'   => $apiKey,
        'is_active' => 1,
    ])->save();
    say("created API user {$apiUser}");
} else {
    // Re-apply the key from .env so a changed key takes effect.
    $user->setNewApiKey($apiKey)->setIsActive(1)->save();
}
$user = Mage::getModel('api/user')->loadByUsername($apiUser);
$user->setRoleIds([$role->getId()])
    ->setRoleUserId($user->getId())
    ->saveRelations();

// --- product -------------------------------------------------------------
$sku = 'pytest-simple';
$product = Mage::getModel('catalog/product');
$productId = $product->getIdBySku($sku);
if (!$productId) {
    $product->setStoreId(0)
        ->setWebsiteIds([$website->getId()])
        ->setAttributeSetId($product->getDefaultAttributeSetId())
        ->setTypeId(Mage_Catalog_Model_Product_Type::TYPE_SIMPLE)
        ->setSku($sku)
        ->setName('Pytest Simple Product')
        ->setDescription('Simple product used by the python-magento integration tests.')
        ->setShortDescription('Integration test product.')
        ->setPrice(10.00)
        ->setWeight(1)
        ->setStatus(Mage_Catalog_Model_Product_Status::STATUS_ENABLED)
        ->setVisibility(Mage_Catalog_Model_Product_Visibility::VISIBILITY_BOTH)
        ->setTaxClassId(0)
        ->setStockData([
            'use_config_manage_stock' => 1,
            'is_in_stock' => 1,
            'qty' => 100000,
        ])
        ->save();
    $productId = $product->getId();
    say("created product {$sku} (id {$productId})");
}
// Orders placed by the tests decrement stock; top it back up every run.
$stock = Mage::getModel('cataloginventory/stock_item')->loadByProduct($productId);
$stock->setQty(100000)->setIsInStock(1)->save();

// --- customer ------------------------------------------------------------
$email = 'pytest.customer@example.com';
$customer = Mage::getModel('customer/customer')
    ->setWebsiteId($website->getId())
    ->loadByEmail($email);
if (!$customer->getId()) {
    $customer->setWebsiteId($website->getId())
        ->setStoreId($website->getDefaultStore()->getId())
        ->setGroupId(1)
        ->setFirstname('Pytest')
        ->setLastname('Customer')
        ->setEmail($email)
        ->setPassword('pytest-password-123')
        ->save();
    say("created customer {$email} (id {$customer->getId()})");
}
if (!$customer->getDefaultBilling()) {
    $region = Mage::getModel('directory/region')->loadByCode('TX', 'US');
    $address = Mage::getModel('customer/address')
        ->setCustomerId($customer->getId())
        ->setFirstname('Pytest')
        ->setLastname('Customer')
        ->setStreet(['1 Test Street'])
        ->setCity('Austin')
        ->setRegionId($region->getId())
        ->setPostcode('73301')
        ->setCountryId('US')
        ->setTelephone('5125550100')
        ->setIsDefaultBilling(1)
        ->setIsDefaultShipping(1)
        ->setSaveInAddressBook(1)
        ->save();
    say("created default address (id {$address->getId()})");
}

// --- indexes + cache -----------------------------------------------------
foreach (Mage::getSingleton('index/indexer')->getProcessesCollection() as $process) {
    $process->reindexEverything();
}
Mage::app()->getCacheInstance()->flush();
say('reindexed and flushed cache');

fwrite(STDOUT, "Seed complete.\n");
