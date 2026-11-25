package com.toobzero.priceradar

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.view.Gravity
import android.view.KeyEvent
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.Button
import android.widget.EditText
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject
import java.text.NumberFormat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : Activity() {
    private val screenBg = Color.rgb(18, 20, 24)
    private val panel = Color.rgb(35, 39, 45)
    private val orange = Color.rgb(255, 151, 54)
    private val muted = Color.rgb(183, 190, 199)

    private data class Store(val id: String, val name: String, val searchUrl: String)

    private val stores = listOf(
        Store("dns", "DNS", "https://www.dns-shop.ru/search/?q="),
        Store("mvideo", "М.Видео", "https://www.mvideo.ru/search?query="),
        Store("ozon", "Ozon", "https://www.ozon.ru/search/?text="),
        Store("wb", "Wildberries", "https://www.wildberries.ru/catalog/0/search.aspx?search="),
        Store("ym", "Яндекс Маркет", "https://market.yandex.ru/search?text=")
    )

    private val preferences by lazy { getSharedPreferences("price_radar_native", MODE_PRIVATE) }
    private val priceFields = linkedMapOf<String, EditText>()
    private val productLinkFields = linkedMapOf<String, EditText>()
    private val offerStatusFields = linkedMapOf<String, TextView>()
    private val searchHistory = mutableListOf<String>()

    private lateinit var queryField: EditText
    private lateinit var cityField: EditText
    private lateinit var historyBlock: LinearLayout
    private lateinit var cardsBlock: LinearLayout
    private lateinit var summary: TextView

    private var currentQuery = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = screenBg
        window.navigationBarColor = screenBg
        loadHistory()
        buildScreen()

        val lastQuery = preferences.getString("last_query", "").orEmpty()
        if (lastQuery.isNotBlank()) {
            queryField.setText(lastQuery)
            performSearch(addToHistory = false)
        }
        handleIncomingIntent(intent)
    }

    private fun buildScreen() {
        val scroll = ScrollView(this).apply {
            setBackgroundColor(screenBg)
            isFillViewport = true
        }
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(28))
        }

        content.addView(TextView(this).apply {
            text = "PRICE RADAR"
            textSize = 27f
            setTextColor(orange)
            gravity = Gravity.CENTER
            letterSpacing = 0.08f
        }, matchWrap())

        content.addView(TextView(this).apply {
            text = "Сравнение цен в пяти магазинах"
            textSize = 16f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            setPadding(0, dp(3), 0, dp(14))
        }, matchWrap())

        content.addView(label("ТОВАР"))
        queryField = editField(
            "Например, телевизор 43 дюйма",
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        )
        queryField.imeOptions = EditorInfo.IME_ACTION_SEARCH
        content.addView(queryField, matchWrap())

        content.addView(label("ГОРОД ДЛЯ ПРОВЕРКИ НАЛИЧИЯ И ДОСТАВКИ"))
        cityField = editField(
            preferences.getString("city", "Санкт-Петербург").orEmpty(),
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        )
        content.addView(cityField, matchWrap())
        content.addView(button("НАСТРОИТЬ API ЯНДЕКС МАРКЕТА", panel, Color.WHITE) {
            showYandexApiSettings()
        }, matchWrap())

        queryField.addTextChangedListener(watcher {
            preferences.edit().putString("last_query", queryField.text.toString()).apply()
        })
        cityField.addTextChangedListener(watcher {
            preferences.edit().putString("city", cityField.text.toString()).apply()
        })
        queryField.setOnEditorActionListener { _, actionId, event ->
            val enter = event?.keyCode == KeyEvent.KEYCODE_ENTER && event.action == KeyEvent.ACTION_UP
            if (actionId == EditorInfo.IME_ACTION_SEARCH || enter) {
                performSearch()
                true
            } else {
                false
            }
        }

        content.addView(button("НАЙТИ В ПЯТИ МАГАЗИНАХ", orange) { performSearch() }, matchWrap())

        historyBlock = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, dp(6), 0, dp(4))
        }
        content.addView(historyBlock, matchWrap())
        renderHistory()

        val notice = TextView(this).apply {
            text = "Цены не выдумываются. Чтобы добавить конкретный товар, открой его карточку в магазине и выбери «Поделиться» → PRICE RADAR. Ссылка сохранится в нужной карточке. Для автоматической цены Яндекс Маркета подключи официальный API ниже; для остальных магазинов пока требуется ручная проверка цены."
            textSize = 13f
            setTextColor(muted)
            setPadding(dp(12), dp(12), dp(12), dp(12))
            setBackgroundColor(panel)
        }
        content.addView(notice, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(8)
            bottomMargin = dp(12)
        })

        cardsBlock = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        content.addView(cardsBlock, matchWrap())

        summary = TextView(this).apply {
            text = "Введи товар и нажми «Найти». Цены появятся здесь после сравнения введённых предложений."
            textSize = 15f
            setTextColor(Color.WHITE)
            setPadding(dp(12), dp(14), dp(12), dp(14))
            setBackgroundColor(panel)
        }
        content.addView(summary, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(10)
        })

        content.addView(button("СРАВНИТЬ ВВЕДЁННЫЕ ЦЕНЫ", orange) { comparePrices() }, matchWrap())
        content.addView(button("ОЧИСТИТЬ ЦЕНЫ", panel, Color.WHITE) { clearPrices() }, matchWrap())

        content.addView(TextView(this).apply {
            text = "Экономия считается только между ценами, которые ты сам проверил на страницах магазинов. Доставка, бонусы, кредитные условия и персональные скидки могут изменить итог."
            textSize = 12f
            setTextColor(muted)
            setPadding(dp(2), dp(8), dp(2), 0)
        }, matchWrap())

        scroll.addView(content)
        setContentView(scroll)
    }

    private fun performSearch(addToHistory: Boolean = true) {
        val query = queryField.text.toString().trim()
        if (query.isBlank()) {
            toast("Сначала введи название товара")
            return
        }

        persistCurrentState()
        currentQuery = query
        preferences.edit()
            .putString("last_query", query)
            .putString("city", cityField.text.toString().trim())
            .apply()

        if (addToHistory) rememberQuery(query)
        renderHistory()
        renderStoreCards(query)
        summary.text = "Для «" + query + "» открой страницы магазинов, внеси цены и нажми «Сравнить». Город проверки: " + cityField.text.toString().ifBlank { "не указан" } + "."
    }

    private fun renderStoreCards(query: String) {
        cardsBlock.removeAllViews()
        priceFields.clear()
        productLinkFields.clear()
        offerStatusFields.clear()

        val saved = try {
            JSONObject(preferences.getString("offers:" + query, "{}").orEmpty())
        } catch (_: Exception) {
            JSONObject()
        }

        stores.forEach { store ->
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(13), dp(12), dp(13), dp(13))
                setBackgroundColor(panel)
            }

            card.addView(TextView(this).apply {
                text = store.name
                textSize = 18f
                setTextColor(orange)
                setPadding(0, 0, 0, dp(5))
            }, matchWrap())

            card.addView(TextView(this).apply {
                text = "Поиск: " + query
                textSize = 12f
                setTextColor(muted)
            }, matchWrap())

            card.addView(button("ОТКРЫТЬ ПОИСК В " + store.name.uppercase(Locale("ru", "RU")), orange) {
                openUrl(store.searchUrl + Uri.encode(query))
            }, LinearLayout.LayoutParams(-1, -2).apply {
                topMargin = dp(8)
                bottomMargin = dp(8)
            })

            card.addView(label("ФАКТИЧЕСКАЯ ЦЕНА, ₽"))
            val price = editField(
                "Введи цену с сайта магазина",
                InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL
            )
            price.setText(saved.optString("price_" + store.id, ""))
            priceFields[store.id] = price
            card.addView(price, matchWrap())
            price.addTextChangedListener(watcher { persistCurrentState() })

            card.addView(label("ССЫЛКА НА КОНКРЕТНЫЙ ТОВАР"))
            val productLink = editField(
                "Вставь ссылку на карточку (необязательно)",
                InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            )
            productLink.setText(saved.optString("url_" + store.id, ""))
            productLinkFields[store.id] = productLink
            card.addView(productLink, matchWrap())
            productLink.addTextChangedListener(watcher { persistCurrentState() })

            if (store.id == "ym") {
                val checkedAt = saved.optLong("checked_ym", 0L)
                val stock = saved.optLong("stock_ym", -1L)
                val apiStatus = TextView(this).apply {
                    textSize = 12f
                    setTextColor(muted)
                    text = if (checkedAt > 0L) {
                        "Источник: API Яндекс Маркета • проверено ${formatTimestamp(checkedAt)}" +
                            if (stock >= 0L) " • остаток: $stock" else ""
                    } else if (hasYandexApiCredentials()) {
                        "API подключён. Нажми обновить после добавления ссылки на товар."
                    } else {
                        "Автоцена доступна после подключения OAuth-токена и place_id."
                    }
                    setPadding(0, dp(7), 0, dp(2))
                }
                offerStatusFields[store.id] = apiStatus
                card.addView(apiStatus, matchWrap())
                card.addView(button("ОБНОВИТЬ ЦЕНУ И НАЛИЧИЕ ИЗ API", Color.rgb(92, 119, 91), Color.WHITE) {
                    fetchYandexMarketOffer(productLink, price, apiStatus)
                }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(6) })
            }

            card.addView(button("ОТКРЫТЬ КАРТОЧКУ ТОВАРА", Color.rgb(92, 119, 91), Color.WHITE) {
                val link = productLinkFields[store.id]?.text?.toString()?.trim().orEmpty()
                if (link.isBlank()) {
                    toast("Сначала вставь ссылку на товар")
                } else if (isWebUrl(link)) {
                    openUrl(link)
                } else {
                    toast("Ссылка должна начинаться с http:// или https://")
                }
            }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(6) })

            cardsBlock.addView(card, LinearLayout.LayoutParams(-1, -2).apply {
                bottomMargin = dp(10)
            })
        }
    }

    private fun hasYandexApiCredentials(): Boolean {
        val placeId = preferences.getString("ym_place_id", "").orEmpty()
        return !SecureTokenStore.read(this).isNullOrBlank() && placeId.toLongOrNull()?.let { it > 0L } == true
    }

    private fun showYandexApiSettings() {
        val form = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(8), dp(20), dp(4))
        }
        val tokenField = EditText(this).apply {
            hint = "OAuth-токен реферальной программы"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            setText(SecureTokenStore.read(this@MainActivity).orEmpty())
            setSingleLine(true)
        }
        val placeIdField = EditText(this).apply {
            hint = "place_id из раздела «Блоги»"
            inputType = InputType.TYPE_CLASS_NUMBER
            setText(preferences.getString("ym_place_id", "").orEmpty())
            setSingleLine(true)
        }
        form.addView(TextView(this).apply {
            text = "Нужны договор и доступ к Реферальной программе Яндекс Маркета. Токен шифруется Android Keystore и не отправляется никуда, кроме официального API Яндекса."
            textSize = 13f
            setTextColor(muted)
            setPadding(0, 0, 0, dp(8))
        }, matchWrap())
        form.addView(label("OAUTH-ТОКЕН"))
        form.addView(tokenField, matchWrap())
        form.addView(label("PLACE_ID"))
        form.addView(placeIdField, matchWrap())

        AlertDialog.Builder(this)
            .setTitle("API Яндекс Маркета")
            .setView(form)
            .setPositiveButton("СОХРАНИТЬ") { _, _ ->
                val token = tokenField.text.toString().trim()
                val placeId = placeIdField.text.toString().trim()
                if (token.isBlank() || placeId.toLongOrNull()?.let { it > 0L } != true) {
                    toast("Нужны OAuth-токен и положительный числовой place_id")
                    return@setPositiveButton
                }
                try {
                    SecureTokenStore.save(this, token)
                    preferences.edit().putString("ym_place_id", placeId).apply()
                    toast("API Яндекс Маркета настроен")
                    if (currentQuery.isNotBlank()) renderStoreCards(currentQuery)
                } catch (e: Exception) {
                    toast("Не удалось сохранить токен: ${e.message?.take(100)}")
                }
            }
            .setNeutralButton("ОТКЛЮЧИТЬ API") { _, _ ->
                SecureTokenStore.clear(this)
                preferences.edit().remove("ym_place_id").apply()
                if (currentQuery.isNotBlank()) renderStoreCards(currentQuery)
                toast("API отключён")
            }
            .setNegativeButton("ОТМЕНА", null)
            .show()
    }

    private fun fetchYandexMarketOffer(linkField: EditText, priceField: EditText, statusView: TextView) {
        val productUrl = linkField.text.toString().trim()
        if (productUrl.isBlank()) {
            toast("Сначала добавь ссылку на карточку Яндекс Маркета")
            return
        }
        val token = SecureTokenStore.read(this).orEmpty()
        val placeId = preferences.getString("ym_place_id", "").orEmpty()
        if (token.isBlank() || placeId.isBlank()) {
            toast("Сначала подключи OAuth-токен и place_id")
            showYandexApiSettings()
            return
        }

        val queryAtRequest = currentQuery
        statusView.text = "Запрашиваю актуальную цену и остаток у Яндекс Маркета…"
        priceField.isEnabled = false
        Thread {
            try {
                val offer = YandexMarketAffiliateClient.fetchProduct(productUrl, token, placeId)
                runOnUiThread {
                    val state = try {
                        JSONObject(preferences.getString("offers:" + queryAtRequest, "{}").orEmpty())
                    } catch (_: Exception) {
                        JSONObject()
                    }
                    state.put("price_ym", offer.priceRub.toString())
                    state.put("url_ym", productUrl)
                    state.put("checked_ym", offer.fetchedAt)
                    state.put("source_ym", "yandex_affiliate_api")
                    offer.title?.let { state.put("title_ym", it) }
                    if (offer.stockAmount != null) state.put("stock_ym", offer.stockAmount)
                    else state.remove("stock_ym")
                    preferences.edit().putString("offers:" + queryAtRequest, state.toString()).apply()

                    if (currentQuery == queryAtRequest) {
                        priceField.setText(offer.priceRub.toString())
                        priceField.isEnabled = true
                        statusView.text = "Источник: API Яндекс Маркета • проверено ${formatTimestamp(offer.fetchedAt)}" +
                            (offer.stockAmount?.let { " • остаток: $it" } ?: "")
                        toast("Получена фактическая цена: ${formatPrice(offer.priceRub.toDouble())} ₽")
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    if (currentQuery == queryAtRequest) {
                        priceField.isEnabled = true
                        statusView.text = "Ошибка обновления: ${e.message?.take(160) ?: "неизвестная ошибка"}"
                        toast("Не удалось получить цену Яндекс Маркета")
                    }
                }
            }
        }.start()
    }

    private fun formatTimestamp(timestamp: Long): String {
        return SimpleDateFormat("dd.MM.yyyy HH:mm", Locale("ru", "RU")).format(Date(timestamp))
    }

    private fun storeForUrl(value: String): Store? {
        val host = try { Uri.parse(value).host?.lowercase().orEmpty() } catch (_: Exception) { "" }
        return when {
            host == "dns-shop.ru" || host.endsWith(".dns-shop.ru") -> stores.first { it.id == "dns" }
            host == "mvideo.ru" || host.endsWith(".mvideo.ru") -> stores.first { it.id == "mvideo" }
            host == "ozon.ru" || host.endsWith(".ozon.ru") || host == "ozon.com" || host.endsWith(".ozon.com") -> stores.first { it.id == "ozon" }
            host == "wildberries.ru" || host.endsWith(".wildberries.ru") -> stores.first { it.id == "wb" }
            host == "market.yandex.ru" || host.endsWith(".market.yandex.ru") ||
                host == "market.yandex.com" || host.endsWith(".market.yandex.com") -> stores.first { it.id == "ym" }
            else -> null
        }
    }

    private fun handleIncomingIntent(incoming: Intent?) {
        if (incoming?.action != Intent.ACTION_SEND) return
        val sharedText = incoming.getStringExtra(Intent.EXTRA_TEXT).orEmpty().trim()
        if (sharedText.isBlank()) return
        val match = Regex("https?://[^\\s<>\\\"']+").find(sharedText)
        if (match == null) {
            toast("В переданном тексте не найдена ссылка на товар")
            return
        }
        val productUrl = match.value.trimEnd('.', ',', ';', ')', ']', '>')
        val store = storeForUrl(productUrl)
        if (store == null) {
            toast("Ссылка не относится к поддерживаемым магазинам")
            return
        }
        val sharedTitle = sharedText.replace(match.value, "").trim().trim('-', ':', '—', '\\n').take(120)
        queryField.setText(sharedTitle.ifBlank { "Товар из ссылки" })
        performSearch()
        val linkField = productLinkFields[store.id]
        linkField?.setText(productUrl)
        persistCurrentState()
        toast("Ссылка добавлена: ${store.name}")
        if (store.id == "ym" && hasYandexApiCredentials()) {
            val priceField = priceFields[store.id]
            val statusView = offerStatusFields[store.id]
            if (linkField != null && priceField != null && statusView != null) {
                fetchYandexMarketOffer(linkField, priceField, statusView)
            }
        }
    }

    override fun onNewIntent(newIntent: Intent) {
        super.onNewIntent(newIntent)
        setIntent(newIntent)
        handleIncomingIntent(newIntent)
    }

    private fun comparePrices() {
        if (priceFields.isEmpty()) {
            toast("Сначала выполни поиск товара")
            return
        }

        val entries = stores.mapNotNull { store ->
            val raw = priceFields[store.id]?.text?.toString().orEmpty()
                .replace(" ", "")
                .replace("\u00A0", "")
                .replace(',', '.')
            val value = raw.toDoubleOrNull()
            if (value != null && value.isFinite() && value > 0) store to value else null
        }

        if (entries.isEmpty()) {
            summary.text = "Нет цен для сравнения. Внеси хотя бы одну фактическую цену."
            return
        }

        val cheapest = entries.minBy { it.second }
        val mostExpensive = entries.maxBy { it.second }
        val average = entries.map { it.second }.average()
        val compared = entries.size

        val result = StringBuilder()
        result.append("ТОВАР: ").append(currentQuery).append('\n')
        result.append("Самая низкая цена: ").append(cheapest.first.name)
            .append(" — ").append(formatPrice(cheapest.second)).append(" ₽\n")
        if (compared >= 2) {
            val saving = mostExpensive.second - cheapest.second
            val percent = if (mostExpensive.second > 0) saving / mostExpensive.second * 100.0 else 0.0
            result.append("Самая высокая: ").append(mostExpensive.first.name)
                .append(" — ").append(formatPrice(mostExpensive.second)).append(" ₽\n")
            result.append("Разница между предложениями: ").append(formatPrice(saving))
                .append(" ₽ (").append(String.format(Locale("ru", "RU"), "%.1f", percent)).append("%)\n")
            result.append("Средняя введённая цена: ").append(formatPrice(average)).append(" ₽\n")
            result.append("Экономия при выборе минимальной цены относительно максимальной: ")
                .append(formatPrice(saving)).append(" ₽")
        } else {
            result.append("Для расчёта экономии добавь цены ещё хотя бы в одном магазине.")
        }
        result.append("\nПроверено магазинов: ").append(compared).append(" из ").append(stores.size)
        summary.text = result.toString()
        persistCurrentState()
    }

    private fun clearPrices() {
        priceFields.values.forEach { it.setText("") }
        if (currentQuery.isNotBlank()) {
            val state = try {
                JSONObject(preferences.getString("offers:" + currentQuery, "{}").orEmpty())
            } catch (_: Exception) {
                JSONObject()
            }
            state.remove("checked_ym")
            state.remove("stock_ym")
            state.remove("source_ym")
            state.remove("title_ym")
            preferences.edit().putString("offers:" + currentQuery, state.toString()).apply()
            offerStatusFields["ym"]?.text = if (hasYandexApiCredentials()) {
                "API подключён. Нажми обновить после добавления ссылки на товар."
            } else {
                "Автоцена доступна после подключения OAuth-токена и place_id."
            }
        }
        summary.text = "Цены очищены. Ссылки на карточки и поисковый запрос сохранены."
        persistCurrentState()
    }

    private fun persistCurrentState() {
        if (currentQuery.isBlank() || priceFields.isEmpty()) return
        val state = try {
            JSONObject(preferences.getString("offers:" + currentQuery, "{}").orEmpty())
        } catch (_: Exception) {
            JSONObject()
        }
        stores.forEach { store ->
            state.put("price_" + store.id, priceFields[store.id]?.text?.toString().orEmpty())
            state.put("url_" + store.id, productLinkFields[store.id]?.text?.toString().orEmpty())
        }
        preferences.edit().putString("offers:" + currentQuery, state.toString()).apply()
    }

    private fun rememberQuery(query: String) {
        searchHistory.removeAll { it.equals(query, ignoreCase = true) }
        searchHistory.add(0, query)
        while (searchHistory.size > 8) searchHistory.removeAt(searchHistory.lastIndex)
        val array = JSONArray()
        searchHistory.forEach { array.put(it) }
        preferences.edit().putString("search_history", array.toString()).apply()
    }

    private fun loadHistory() {
        try {
            val array = JSONArray(preferences.getString("search_history", "[]").orEmpty())
            for (i in 0 until array.length()) {
                val value = array.optString(i).trim()
                if (value.isNotBlank() && !searchHistory.contains(value)) searchHistory.add(value)
            }
        } catch (_: Exception) {
            searchHistory.clear()
        }
    }

    private fun renderHistory() {
        if (!::historyBlock.isInitialized) return
        historyBlock.removeAllViews()
        if (searchHistory.isEmpty()) return

        historyBlock.addView(label("НЕДАВНИЕ ЗАПРОСЫ"))
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        searchHistory.forEach { item ->
            row.addView(button(item, panel, Color.WHITE) {
                queryField.setText(item)
                performSearch()
            }, LinearLayout.LayoutParams(-2, -2).apply {
                rightMargin = dp(7)
            })
        }
        val horizontal = HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            addView(row)
        }
        historyBlock.addView(horizontal, matchWrap())
    }

    private fun openUrl(url: String) {
        if (!isWebUrl(url)) {
            toast("Некорректная ссылка")
            return
        }
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: Exception) {
            toast("Не удалось открыть ссылку. Проверь браузер.")
        }
    }

    private fun isWebUrl(value: String): Boolean {
        val uri = try { Uri.parse(value) } catch (_: Exception) { return false }
        return uri.scheme == "https" || uri.scheme == "http"
    }

    private fun editField(hintText: String, type: Int): EditText {
        return EditText(this).apply {
            hint = hintText
            inputType = type
            setTextColor(Color.WHITE)
            setHintTextColor(Color.rgb(145, 151, 160))
            textSize = 14f
            isSingleLine = true
            setPadding(dp(11), dp(9), dp(11), dp(9))
            setBackgroundColor(screenBg)
        }
    }

    private fun label(value: String): TextView {
        return TextView(this).apply {
            text = value
            textSize = 11f
            setTextColor(muted)
            setPadding(0, dp(8), 0, dp(5))
        }
    }

    private fun button(
        value: String,
        color: Int,
        textColor: Int = Color.BLACK,
        action: () -> Unit
    ): Button {
        return Button(this).apply {
            text = value
            isAllCaps = false
            textSize = 13f
            setTextColor(textColor)
            setBackgroundColor(color)
            setPadding(dp(10), dp(4), dp(10), dp(4))
            setOnClickListener { action() }
        }
    }

    private fun watcher(onChange: () -> Unit): TextWatcher {
        return object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = onChange()
            override fun afterTextChanged(s: Editable?) = Unit
        }
    }

    private fun formatPrice(value: Double): String {
        return NumberFormat.getIntegerInstance(Locale("ru", "RU")).format(value)
    }

    private fun matchWrap() = LinearLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT,
        ViewGroup.LayoutParams.WRAP_CONTENT
    )

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

    override fun onPause() {
        persistCurrentState()
        super.onPause()
    }
}
