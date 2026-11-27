package com.toobzero.priceradar

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener

class StoreSearchActivity : Activity() {
    companion object {
        const val EXTRA_STORE_ID = "store_id"
        const val EXTRA_STORE_NAME = "store_name"
        const val EXTRA_SEARCH_URL = "search_url"
        const val EXTRA_QUERY = "query"
        const val EXTRA_SELECTED_OFFER = "selected_offer"
    }

    private val screenBackground = Color.rgb(18, 20, 24)
    private val orange = Color.rgb(255, 151, 54)
    private val muted = Color.rgb(183, 190, 199)
    private lateinit var webView: WebView
    private lateinit var status: TextView
    private var storeId = ""
    private var storeName = ""
    private var query = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        storeId = intent.getStringExtra(EXTRA_STORE_ID).orEmpty()
        storeName = intent.getStringExtra(EXTRA_STORE_NAME).orEmpty()
        query = intent.getStringExtra(EXTRA_QUERY).orEmpty()
        val searchUrl = intent.getStringExtra(EXTRA_SEARCH_URL).orEmpty()
        if (storeId.isBlank() || storeName.isBlank() || query.isBlank() || searchUrl.isBlank()) {
            finish()
            return
        }

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(screenBackground)
        }
        val top = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(8), dp(12), dp(8))
            setBackgroundColor(screenBackground)
        }
        top.addView(button("←  Назад", Color.rgb(45, 49, 55), Color.WHITE) {
            if (webView.canGoBack()) webView.goBack() else finish()
        }, wrap())
        top.addView(TextView(this).apply {
            text = storeName + " · " + query
            setTextColor(Color.WHITE)
            textSize = 16f
            setPadding(0, dp(8), 0, dp(4))
        }, wrap())
        status = TextView(this).apply {
            text = "Загрузка страницы поиска…"
            setTextColor(muted)
            textSize = 12f
        }
        top.addView(status, wrap())
        root.addView(top, wrap())

        webView = WebView(this).apply {
            setBackgroundColor(Color.WHITE)
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.loadsImagesAutomatically = true
            settings.useWideViewPort = true
            settings.loadWithOverviewMode = true
            settings.setSupportZoom(true)
            settings.builtInZoomControls = true
            settings.displayZoomControls = false
            webChromeClient = WebChromeClient()
            webViewClient = object : WebViewClient() {
                override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                    status.text = "Загрузка: " + (url?.let { Uri.parse(it).host } ?: storeName)
                }
                override fun onPageFinished(view: WebView?, url: String?) {
                    status.text = "Страница открыта. Считай карточки, затем проверь выбранный товар."
                }
                override fun onReceivedError(
                    view: WebView?,
                    request: android.webkit.WebResourceRequest?,
                    error: android.webkit.WebResourceError?
                ) {
                    if (request?.isForMainFrame == true) status.text = "Не удалось загрузить страницу. Можно открыть её в браузере."
                }
            }
        }
        root.addView(webView, LinearLayout.LayoutParams(-1, 0, 1f))

        val bottom = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(8), dp(12), dp(12))
            setBackgroundColor(screenBackground)
        }
        bottom.addView(button("СЧИТАТЬ КАРТОЧКИ И ЦЕНЫ", orange, Color.BLACK) {
            scanCurrentPage()
        }, wrap())
        bottom.addView(button("ОТКРЫТЬ В БРАУЗЕРЕ", Color.rgb(45, 49, 55), Color.WHITE) {
            try {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(webView.url ?: searchUrl)))
            } catch (_: Exception) {
                Toast.makeText(this, "Не удалось открыть браузер", Toast.LENGTH_SHORT).show()
            }
        }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(6) })
        root.addView(bottom, wrap())
        setContentView(root)
        webView.loadUrl(searchUrl + Uri.encode(query))
    }

    private fun scanCurrentPage() {
        status.text = "Проверяю видимые карточки и цены…"
        val script = """
            JSON.stringify((function() {
                const priceRx = /([0-9][0-9\s\u00a0]{0,12}(?:[.,][0-9]{1,2})?)\s*(?:₽|руб(?:\.|ля|лей)?|р\.?)(?![a-zа-я])/gi;
                const badPrice = /в\s*месяц|\/мес|мес\.|рассроч|кредит|подписк|балл|кешбек/i;
                const priceLineRx = /(?:₽|руб(?:\.|ля|лей)?|р\.?)/i;
                const domainRules = {dns:'dns-shop.ru', mvideo:'mvideo.ru', ozon:'ozon.ru', wb:'wildberries.ru', ym:'market.yandex.ru'};
                const rootDomain = domainRules["$storeId"];
                const productPathRules = {
                    dns: p => { const s=p.split('/').filter(Boolean); return s.length>=2 && s[0]==='product'; },
                    mvideo: p => { const s=p.split('/').filter(Boolean); return s.length>=2 && (s[0]==='products' || s[0]==='product'); },
                    ozon: p => { const s=p.split('/').filter(Boolean); return s.length>=2 && s[0]==='product'; },
                    wb: p => { const s=p.split('/').filter(Boolean); return s.length>=2 && s[0]==='catalog' && s[1].length>0 && s[1].split('').every(c=>c>='0' && c<='9') && s[1]!=='0' && (s.length===2 || (s.length===3 && s[2].toLowerCase()==='detail.aspx')); },
                    ym: p => { const s=p.split('/').filter(Boolean); return s.length>=2 && (s[0].startsWith('product--') || s[0]==='card' || s[0]==='product'); }
                };
                const results = [];
                const seen = new Set();
                const anchors = Array.from(document.querySelectorAll('a[href]'));
                for (const a of anchors) {
                    if (a.getClientRects && !a.getClientRects().length) continue;
                    let u;
                    try { u = new URL(a.href, location.href); } catch (e) { continue; }
                    if (u.protocol !== 'https:' || !(u.hostname === rootDomain || u.hostname.endsWith('.' + rootDomain)) ||
                        !productPathRules["$storeId"](u.pathname) ||
                        /search|catalog\/0|cart|account|login|help|compare|favorite|promotion/i.test(u.pathname + u.search)) continue;
                    let node = a, cardText = '', card = null;
                    for (let depth = 0; node && depth < 7; depth++, node = node.parentElement) {
                        const t = (node.innerText || '').trim();
                        priceRx.lastIndex = 0;
                        if (t.length >= 25 && t.length <= 1200 && priceRx.test(t)) { card = node; cardText = t; break; }
                        priceRx.lastIndex = 0;
                    }
                    if (!card || badPrice.test(cardText)) continue;
                    const prices = [];
                    let m;
                    priceRx.lastIndex = 0;
                    while ((m = priceRx.exec(cardText)) !== null) {
                        const p = Number(m[1].replace(/[\s\u00a0]/g, '').replace(',', '.'));
                        const ctx = cardText.slice(Math.max(0, m.index - 35), Math.min(cardText.length, m.index + 55));
                        if (Number.isFinite(p) && p >= 50 && p <= 50000000 && !badPrice.test(ctx)) prices.push(p);
                    }
                    priceRx.lastIndex = 0;
                    if (!prices.length) continue;
                    const price = Math.min.apply(null, prices);
                    const nameNode = card.querySelector('h3,h2,[itemprop=name]');
                    const imageNode = a.querySelector('img');
                    let title = ((nameNode && nameNode.innerText) || a.innerText || a.getAttribute('title') || (imageNode && imageNode.alt) || '').trim();
                    if (!title) {
                        const lines = cardText.split(/\n/).map(s => s.trim()).filter(s => s.length >= 6 && s.length <= 180 && !priceLineRx.test(s) && !badPrice.test(s));
                        lines.sort((x, y) => y.length - x.length);
                        title = lines[0] || '';
                    }
                    priceRx.lastIndex = 0;
                    title = title.replace(priceRx, '').replace(/\s+/g, ' ').trim();
                    priceRx.lastIndex = 0;
                    if (title.length < 5 || seen.has(u.href)) continue;
                    seen.add(u.href);
                    results.push({title:title.slice(0,180), price:price, url:u.href});
                    if (results.length >= 30) break;
                }
                return results;
            })())
        """.trimIndent()
        webView.evaluateJavascript(script) { encoded ->
            try {
                val decoded = JSONTokener(encoded).nextValue() as? String ?: "[]"
                showCandidates(JSONArray(decoded))
            } catch (_: Exception) {
                status.text = "Не удалось разобрать страницу. Возможно, сайт изменил разметку."
                Toast.makeText(this, "Карточки не распознаны", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showCandidates(array: JSONArray) {
        if (array.length() == 0) {
            status.text = "Не найдены карточки с распознаваемой ценой. CAPTCHA, динамическая выдача или другая разметка могут мешать."
            Toast.makeText(this, "На странице не удалось найти предложения", Toast.LENGTH_LONG).show()
            return
        }
        val items = Array(array.length()) { i ->
            val o = array.optJSONObject(i) ?: JSONObject()
            val price = o.optDouble("price", 0.0)
            val title = o.optString("title", "Товар")
            title + "\n" + formatPrice(price) + " ₽ · предварительно"
        }
        AlertDialog.Builder(this)
            .setTitle("Найденные кандидаты: " + array.length())
            .setMessage("Цена считана с текущей страницы и не подтверждена. Открой карточку товара и проверь цену, наличие и регион перед сравнением.")
            .setItems(items) { _, which ->
                val chosen = array.optJSONObject(which) ?: return@setItems
                val offer = JSONObject(chosen.toString())
                offer.put("store_id", storeId)
                offer.put("store_name", storeName)
                offer.put("query", query)
                offer.put("scan_time", System.currentTimeMillis())
                setResult(RESULT_OK, Intent().putExtra(EXTRA_SELECTED_OFFER, offer.toString()))
                finish()
            }
            .setNegativeButton("Отмена", null)
            .show()
        status.text = "Распознано " + array.length() + " кандидатов. Цена предварительная."
    }

    private fun button(text: String, color: Int, textColor: Int, action: () -> Unit): Button {
        return Button(this).apply {
            this.text = text
            isAllCaps = false
            textSize = 13f
            setTextColor(textColor)
            setBackgroundColor(color)
            setPadding(dp(8), dp(3), dp(8), dp(3))
            setOnClickListener { action() }
        }
    }

    private fun formatPrice(value: Double): String =
        java.text.NumberFormat.getIntegerInstance(java.util.Locale("ru", "RU")).format(value)

    private fun wrap() = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    @Suppress("DEPRECATION")
    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }
    override fun onDestroy() {
        if (::webView.isInitialized) {
            webView.stopLoading()
            webView.destroy()
        }
        super.onDestroy()
    }
}
