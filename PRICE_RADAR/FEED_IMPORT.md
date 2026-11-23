# RSS/Atom ingestion (configured feeds only)

This connector reads public RSS/Atom feeds that the project owner has explicitly configured and is permitted to use. It does not crawl marketplaces, bypass logins, CAPTCHA, rate limits, paywalls, or robots/terms restrictions.

## Run
```bash
python PRICE_RADAR/tools/import_feeds.py PRICE_RADAR/feeds.example.json -o offers.json
```

1. Obtain a feed URL from a Russian seller, retailer, or partner that explicitly permits this use.
2. Replace the placeholder URL and set `enabled` to `true`.
3. Keep `source` as a canonical source name or `partner`; set the seller's Russian region in `location`.
4. Run the importer. Only entries with a title, HTTPS link, positive parsed price, and RUB currency are emitted.

The importer supports RSS 2.0 and Atom basics. It extracts price only from explicit `price`/`amount` XML fields or a clear ruble amount in the description. Entries without a reliably parsed price are discarded rather than guessed. Every emitted record is marked as newly observed by the normalizer; a feed response is not proof that an item remains available later.

No real marketplace feed is configured by default. Do not enable a source until its owner has confirmed permission and the feed format has been tested.
