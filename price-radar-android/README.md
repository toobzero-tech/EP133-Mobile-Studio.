# PRICE RADAR Android 1.2.0

Native Android app for comparing search results from DNS, М.Видео, Ozon, Wildberries and Яндекс Маркет.

## 1.2.0 changes
- Store searches open inside the app in a native WebView screen.
- Added a "Считать карточки и цены" action that reads visible product-card text from the current page.
- Parser searches for product-like links and ruble price text, rejects unrelated hostnames, deduplicates direct links, and excludes cards containing installment/monthly-payment signals.
- User can choose a candidate; its detected price and direct product link are imported into the main comparison screen.
- Scan timestamps are saved per store/query and shown as a preliminary source indicator.
- Imported prices are explicitly marked as preliminary and are not guaranteed to represent the final price, availability, region, or discount conditions.
- Added Internet permission, declared the WebView search activity, and bumped app version to 1.2.0.

## Important limitations
The parser reads the currently rendered public search page. It does not bypass CAPTCHA, bot protections, login walls, or access controls. Retailer pages are dynamic and may change their markup; scanning can return no results or misread a price. Every imported candidate must be checked on its product page before comparison or purchase.

This is not a server-side feed and does not silently update prices in the background. The user opens a store search, taps "Считать карточки и цены", and selects a candidate. Official/partner APIs and a reliable cross-store feed remain a separate integration stage.

## App details
- Application ID: com.toobzero.priceradar
- Minimum Android: 9 / API 28
- Target SDK: 35
- Java: 17
- Android Gradle Plugin: 8.7.3
- Kotlin plugin: 2.0.21

## Build
The main build is GitHub Actions: .github/workflows/build-price-radar-android.yml. The Colab notebook is an optional fallback. Parser smoke tests can be run with node tests_store_parser.js. They use synthetic DOM objects and verify parser behavior, not live store connectivity.
