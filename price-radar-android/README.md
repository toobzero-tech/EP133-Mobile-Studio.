# PRICE RADAR Android 1.2.2

Native Android app for searching and comparing offers from DNS, М.Видео, Ozon, Wildberries and Яндекс Маркет.

## 1.2.2 changes
- Keeps in-app WebView searches and visible-card price parsing from 1.2.0.
- Adds a per-store manual confirmation step for each imported or typed offer.
- A price is counted only after the user confirms it and the offer URL is HTTPS on that store's domain.
- Changing a confirmed price or link invalidates the confirmation; it must be confirmed again.
- Comparison excludes preliminary, unconfirmed prices and reports how many were excluded.
- Confirmation timestamps persist per search and store.
- Clears price and confirmation states together.
- Scanned and manually entered links must match a store-specific product URL path; home/search pages are rejected.
- The page scanner accepts only HTTPS product links.
- Price parsing handles narrow no-break spaces (U+202F) used in Russian number formatting.

## Limits
The visible-page parser is preliminary and can misread a dynamic retailer page, promotional text, or variant price. It does not bypass CAPTCHA, bot protection, login walls, or access controls. Confirmation means the user reviewed the price/link, not that the app independently guarantees stock, delivery, discount eligibility, or authenticity. Availability and shipping should still be checked on the product page.

Automatic cross-store price refresh is not implemented. It requires a reliable permitted data source/API for each retailer. The app does not fabricate prices.

## App
- Package: `com.toobzero.priceradar`
- Minimum Android: 9 (API 28)
- Target SDK: 35
- Java: 17
- Android Gradle Plugin: 8.7.3
- Kotlin plugin: 2.0.21

## Build
GitHub Actions workflow: `.github/workflows/build-price-radar-android.yml`.
Node smoke tests:
- `node tests_store_parser.js`
- `node tests_offer_confirmation.js`

The build workflow packages the source ZIP as a separate artifact.