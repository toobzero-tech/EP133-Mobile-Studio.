const fs = require('fs');
const path = require('path');

const sourcePath = path.join(__dirname, 'app/src/main/java/com/toobzero/priceradar/StoreSearchActivity.kt');
const source = fs.readFileSync(sourcePath, 'utf8');
const marker = 'val script = """';
const start = source.indexOf(marker);
if (start < 0) throw new Error('Parser script marker not found in Kotlin source');
const scriptStart = start + marker.length;
const scriptEnd = source.indexOf('""".trimIndent()', scriptStart);
if (scriptEnd < 0) throw new Error('Parser script end marker not found');
const template = source.slice(scriptStart, scriptEnd).trim();

function runScan(storeId, host, anchors) {
  const script = template.replaceAll('$storeId', storeId);
  const document = { querySelectorAll: () => anchors };
  const location = { href: 'https://' + host + '/search?q=test' };
  return JSON.parse(new Function('document', 'location', 'return ' + script)(document, location));
}
function anchor(host, href, cardText, title) {
  const card = {
    innerText: cardText,
    parentElement: null,
    querySelector: () => ({ innerText: title })
  };
  return {
    href,
    innerText: '',
    getAttribute: () => null,
    querySelector: () => ({ alt: '' }),
    getClientRects: () => [{}],
    parentElement: card
  };
}
const fixtures = [
  ['dns', 'dns-shop.ru', 'https://www.dns-shop.ru/product/abc/tv/', 'Samsung TV 43 4K, HDR smart television\n42 990 ₽', 'Samsung 43-inch TV', 42990],
  ['mvideo', 'mvideo.ru', 'https://www.mvideo.ru/products/tv-123', 'Smart television model, HDR\n36 499 руб.', 'TV model', 36499],
  ['ozon', 'ozon.ru', 'https://www.ozon.ru/product/tv-123', 'Smart TV 43 inch model, UHD resolution\n39 990 ₽', 'Ozon TV', 39990],
  ['wb', 'wildberries.ru', 'https://www.wildberries.ru/catalog/123456/detail.aspx', 'Smart TV 43 inch model, UHD resolution\n35 999 ₽', 'Wildberries TV', 35999],
  ['ym', 'market.yandex.ru', 'https://market.yandex.ru/product--tv/123', 'Smart TV 43 inch model, UHD resolution\n40 990 ₽', 'Yandex TV', 40990]
];
let failed = 0;
for (const [store, host, url, text, title, expectedPrice] of fixtures) {
  const found = runScan(store, host, [anchor(host, url, text, title)]);
  const pass = found.length === 1 && found[0].price === expectedPrice && found[0].url === url;
  console.log((pass ? 'PASS' : 'FAIL') + ' parser: ' + store);
  if (!pass) { console.error(found); failed++; }
}
const monthly = runScan('dns', 'dns-shop.ru', [anchor('dns-shop.ru', 'https://www.dns-shop.ru/product/monthly/', 'TV\n999 ₽/мес\n42 990 ₽', 'Monthly TV')]);
const passMonthly = monthly.length === 0;
console.log((passMonthly ? 'PASS' : 'FAIL') + ' monthly/installment price filter');
if (!passMonthly) { console.error(monthly); failed++; }
const spoof = runScan('dns', 'dns-shop.ru', [anchor('dns-shop.ru', 'https://www.dns-shop.ru.attacker.example/product/x', 'Product name long enough\n12 345 ₽', 'Spoof')]);
const passSpoof = spoof.length === 0;
console.log((passSpoof ? 'PASS' : 'FAIL') + ' off-domain link rejection');
if (!passSpoof) { console.error(spoof); failed++; }
const dup = runScan('dns', 'dns-shop.ru', [
  anchor('dns-shop.ru', 'https://www.dns-shop.ru/product/dup/', 'Product name long enough\n12 345 ₽', 'Duplicate'),
  anchor('dns-shop.ru', 'https://www.dns-shop.ru/product/dup/', 'Product name long enough\n12 345 ₽', 'Duplicate')
]);
const passDup = dup.length === 1;
console.log((passDup ? 'PASS' : 'FAIL') + ' duplicate link rejection');
if (!passDup) { console.error(dup); failed++; }
if (failed) process.exit(1);
console.log('All parser checks passed.');
