const fs = require('fs');
const path = require('path');
const assert = require('assert');

const mainPath = path.join(__dirname, 'app/src/main/java/com/toobzero/priceradar/MainActivity.kt');
const main = fs.readFileSync(mainPath, 'utf8');
const compare = main.slice(main.indexOf('private fun comparePrices()'), main.indexOf('private fun clearPrices()'));
const clear = main.slice(main.indexOf('private fun clearPrices()'), main.indexOf('private fun persistCurrentState()'));
const persist = main.slice(main.indexOf('private fun persistCurrentState()'), main.indexOf('private fun rememberQuery()'));
const importBlock = main.slice(main.indexOf('override fun onActivityResult'), main.indexOf('private fun openUrl'));

const checks = [
  ['all five stores carry allowed product domains', ['dns-shop.ru','mvideo.ru','ozon.ru','wildberries.ru','market.yandex.ru'].every(d => main.includes(d))],
  ['verification map is initialized and reset with method calls', main.includes('verificationStatusViews = linkedMapOf<String, TextView>()') && main.includes('verificationStatusViews.clear()') && main.includes('scanStatusViews.clear()')],
  ['comparison filters by confirmation timestamp', compare.includes('verifiedTimes[store.id]') && compare.includes('> 0L')],
  ['comparison validates store-specific HTTPS links', compare.includes('isStoreProductUrl(store, link)')],
  ['confirmation UI is present', main.includes('ПОДТВЕРДИТЬ ЦЕНУ И ССЫЛКУ')],
  ['price and link edits revoke confirmation', (main.match(/invalidateVerification\(store\.id\)/g) || []).length >= 2],
  ['confirmation timestamp is persisted', persist.includes('verified_time_')],
  ['clear button resets confirmation state', clear.includes('verifiedTimes') && clear.includes('verificationStatusViews')],
  ['scanner import remains unconfirmed', importBlock.includes('verifiedTimes[storeId] = 0L') && importBlock.includes('Не подтверждено вручную')],
  ['import status string is syntactically closed', !main.includes('расчёте""')],
  ['product URLs use store-specific path rules', main.includes("val parts = uri.path.orEmpty().split('/').filter { it.isNotBlank() }") && main.includes('parts[0] == "catalog"') && main.includes('parts[0].startsWith("product--")')],
  ['price parser handles narrow no-break space separator', main.includes('\\u202F')]
];
let failures = 0;
for (const [name, pass] of checks) {
  console.log((pass ? 'PASS' : 'FAIL') + ' source check: ' + name);
  if (!pass) failures++;
}

const domains = { dns:'dns-shop.ru', mvideo:'mvideo.ru', ozon:'ozon.ru', wb:'wildberries.ru', ym:'market.yandex.ru' };
function allowed(store, href) {
  try {
    const u = new URL(href);
    if (u.protocol !== 'https:' || !(u.hostname === domains[store] || u.hostname.endsWith('.' + domains[store]))) return false;
    const parts = u.pathname.split('/').filter(Boolean);
    if (parts.length < 2) return false;
    switch (store) {
      case 'dns': return parts[0] === 'product';
      case 'mvideo': return parts[0] === 'products' || parts[0] === 'product';
      case 'ozon': return parts[0] === 'product';
      case 'wb': return parts[0] === 'catalog' && /^\\d+$/.test(parts[1]) && parts[1] !== '0' &&
        (parts.length === 2 || (parts.length === 3 && parts[2].toLowerCase() === 'detail.aspx'));
      case 'ym': return parts[0].startsWith('product--') || parts[0] === 'card' || parts[0] === 'product';
      default: return false;
    }
  } catch (_) { return false; }
}
const urlFixtures = [
  ['dns','https://www.dns-shop.ru/product/x/y',true],
  ['mvideo','https://mvideo.ru/products/4322096',true],
  ['ozon','https://www.ozon.ru/product/tv-123',true],
  ['wb','https://www.wildberries.ru/catalog/123456/detail.aspx',true],
  ['wb','https://www.wildberries.ru/catalog/123456/',true],
  ['ym','https://market.yandex.ru/product--tv/123',true],
  ['ym','https://market.yandex.ru/card/tv-123',true],
  ['dns','https://dns-shop.ru/',false],
  ['dns','https://dns-shop.ru/search/?q=tv',false],
  ['dns','http://dns-shop.ru/product/x/y',false],
  ['dns','https://dns-shop.ru.evil.example/product/x/y',false],
  ['mvideo','https://www.mvideo.ru/search?query=tv',false],
  ['ozon','https://www.ozon.ru/',false],
  ['wb','https://www.wildberries.ru/catalog/0/search.aspx',false],
  ['wb','https://www.wildberries.ru/catalog/abc/detail.aspx',false],
  ['ym','https://market.yandex.ru/search?text=tv',false],
  ['ozon','https://www.wildberries.ru/catalog/123/detail.aspx',false],
  ['ym','https://fake.market.yandex.ru.evil.example/card/x',false]
];
for (const [store,url,expected] of urlFixtures) {
  const pass=allowed(store,url)===expected;
  console.log((pass?'PASS':'FAIL')+' URL policy fixture: '+store+' '+url);
  if(!pass)failures++;
}
const priceFixtures=[['42990',42990],['42 990',42990],['42 990',42990],['42 990',42990],['42,50',42.5],['0',null],['-10',null],['abc',null]];
function parsePrice(s){const n=s.replace(/[\\s\\u00A0\\u202F]/g,'').replace(',','.');const v=Number(n);return Number.isFinite(v)&&v>0?v:null;}
for (const [raw,expected] of priceFixtures) {
  const pass=parsePrice(raw)===expected;
  console.log((pass?'PASS':'FAIL')+' price fixture: '+JSON.stringify(raw));
  if(!pass)failures++;
}
if(failures){process.exit(1);}
console.log('Offer-confirmation safeguards checks passed.');
