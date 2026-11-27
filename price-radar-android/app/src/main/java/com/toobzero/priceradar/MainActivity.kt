package com.toobzero.priceradar

import android.app.Activity
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

    private data class Store(val id: String, val name: String, val searchUrl: String, val domain: String)

    private val stores = listOf(
        Store("dns", "DNS", "https://www.dns-shop.ru/search/?q=", "dns-shop.ru"),
        Store("mvideo", "М.Видео", "https://www.mvideo.ru/search?query=", "mvideo.ru"),
        Store("ozon", "Ozon", "https://www.ozon.ru/search/?text=", "ozon.ru"),
        Store("wb", "Wildberries", "https://www.wildberries.ru/catalog/0/search.aspx?search=", "wildberries.ru"),
        Store("ym", "Яндекс Маркет", "https://market.yandex.ru/search?text=", "market.yandex.ru")
    )

    private val preferences by lazy { getSharedPreferences("price_radar_native", MODE_PRIVATE) }
    private val priceFields = linkedMapOf<String, EditText>()
    private val productLinkFields = linkedMapOf<String, EditText>()
    private val scanTimes = linkedMapOf<String, Long>()
    private val scanStatusViews = linkedMapOf<String, TextView>()
    private val verifiedTimes = linkedMapOf<String, Long>()
    private val verificationStatusViews = linkedMapOf<String, TextView>()
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
            text = "Важно: считанные цены предварительные. Перед сравнением открой карточку товара, проверь цену, наличие, регион и условия доставки, вставь прямую HTTPS-ссылку и нажми «Подтвердить». Неподтверждённые цены не участвуют в расчёте."
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
        scanTimes.clear()
        scanStatusViews.clear()
        verifiedTimes.clear()
        verificationStatusViews.clear()

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
                openStoreSearch(store, query)
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
            price.addTextChangedListener(watcher {
                invalidateVerification(store.id)
                persistCurrentState()
            })

            card.addView(label("ССЫЛКА НА КОНКРЕТНЫЙ ТОВАР"))
            val productLink = editField(
                "Вставь ссылку на карточку (необязательно)",
                InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            )
            productLink.setText(saved.optString("url_" + store.id, ""))
            productLinkFields[store.id] = productLink
            card.addView(productLink, matchWrap())
            productLink.addTextChangedListener(watcher {
                invalidateVerification(store.id)
                persistCurrentState()
            })

            val verifiedAt = saved.optLong("verified_time_" + store.id, 0L)
            verifiedTimes[store.id] = verifiedAt
            val verificationStatus = TextView(this).apply {
                val storedPrice = parsePrice(price.text.toString())
                val storedLink = productLink.text.toString().trim()
                text = when {
                    verifiedAt > 0L && storedPrice != null && isStoreProductUrl(store, storedLink) ->
                        "Проверено вручную: " + formatScanTime(verifiedAt)
                    verifiedAt > 0L -> "Проверка сохранена, но цена или ссылка некорректна. Подтверди заново."
                    else -> "Не подтверждено вручную. Предварительная цена не учитывается."
                }
                textSize = 11f
                setTextColor(muted)
                setPadding(0, dp(4), 0, dp(2))
            }
            verificationStatusViews[store.id] = verificationStatus
            card.addView(verificationStatus, matchWrap())

            card.addView(button("ПОДТВЕРДИТЬ ЦЕНУ И ССЫЛКУ", Color.rgb(65, 105, 76), Color.WHITE) {
                val enteredPrice = parsePrice(price.text.toString())
                val enteredLink = productLink.text.toString().trim()
                when {
                    enteredPrice == null -> toast("Введи корректную положительную цену")
                    !isStoreProductUrl(store, enteredLink) -> toast("Нужна HTTPS-ссылка на товар именно в " + store.domain)
                    else -> {
                        val confirmedAt = System.currentTimeMillis()
                        verifiedTimes[store.id] = confirmedAt
                        verificationStatus.text = "Проверено вручную: " + formatScanTime(confirmedAt)
                        persistCurrentState()
                        summary.text = "Предложение " + store.name + " подтверждено вручную. Оно будет участвовать в сравнении."
                        toast("Цена и ссылка подтверждены")
                    }
                }
            }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(6) })

            val scanStatus = TextView(this).apply {
                val scanned = saved.optLong("scan_time_" + store.id, 0L)
                scanTimes[store.id] = scanned
                text = if (scanned > 0L) "Считано со страницы: " + formatScanTime(scanned) + " · предварительно" else "Автоматическое считывание не выполнено"
                textSize = 11f
                setTextColor(muted)
                setPadding(0, dp(4), 0, dp(2))
            }
            scanStatusViews[store.id] = scanStatus
            card.addView(scanStatus, matchWrap())

            card.addView(button("ОТКРЫТЬ КАРТОЧКУ ТОВАРА", Color.rgb(92, 119, 91), Color.WHITE) {
                val link = productLinkFields[store.id]?.text?.toString()?.trim().orEmpty()
                if (link.isBlank()) {
                    toast("Сначала вставь ссылку на товар")
                } else if (isStoreProductUrl(store, link)) {
                    openUrl(link)
                } else {
                    toast("Вставь HTTPS-ссылку на товар именно в " + store.domain)
                }
            }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(6) })

            cardsBlock.addView(card, LinearLayout.LayoutParams(-1, -2).apply {
                bottomMargin = dp(10)
            })
        }
    }

    private fun comparePrices() {
        if (priceFields.isEmpty()) {
            toast("Сначала выполни поиск товара")
            return
        }

        val unverifiedCount = stores.count { store ->
            parsePrice(priceFields[store.id]?.text?.toString().orEmpty()) != null &&
                ((verifiedTimes[store.id] ?: 0L) <= 0L ||
                    !isStoreProductUrl(store, productLinkFields[store.id]?.text?.toString().orEmpty()))
        }
        val entries = stores.mapNotNull { store ->
            val value = parsePrice(priceFields[store.id]?.text?.toString().orEmpty())
            val link = productLinkFields[store.id]?.text?.toString().orEmpty()
            if (value != null && (verifiedTimes[store.id] ?: 0L) > 0L && isStoreProductUrl(store, link)) store to value else null
        }

        if (entries.isEmpty()) {
            summary.text = if (unverifiedCount > 0) {
                "Есть $unverifiedCount предварительных цен, но они не участвуют в расчёте. Открой товар, проверь цену и ссылку, затем нажми «Подтвердить цену и ссылку»."
            } else {
                "Нет подтверждённых цен для сравнения. Внеси цену и HTTPS-ссылку на товар, проверь их и нажми «Подтвердить»."
            }
            return
        }

        val cheapest = entries.minBy { it.second }
        val mostExpensive = entries.maxBy { it.second }
        val average = entries.map { it.second }.average()
        val compared = entries.size

        val result = StringBuilder()
        result.append("ТОВАР: ").append(currentQuery).append('\n')
        result.append("Самая низкая подтверждённая цена: ").append(cheapest.first.name)
            .append(" — ").append(formatPrice(cheapest.second)).append(" ₽\n")
        if (compared >= 2) {
            val saving = mostExpensive.second - cheapest.second
            val percent = if (mostExpensive.second > 0) saving / mostExpensive.second * 100.0 else 0.0
            result.append("Самая высокая подтверждённая: ").append(mostExpensive.first.name)
                .append(" — ").append(formatPrice(mostExpensive.second)).append(" ₽\n")
            result.append("Разница между подтверждёнными предложениями: ").append(formatPrice(saving))
                .append(" ₽ (").append(String.format(Locale("ru", "RU"), "%.1f", percent)).append("%)\n")
            result.append("Средняя подтверждённая цена: ").append(formatPrice(average)).append(" ₽\n")
            result.append("Экономия относительно самой дорогой подтверждённой цены: ")
                .append(formatPrice(saving)).append(" ₽")
        } else {
            result.append("Для расчёта экономии нужно минимум два подтверждённых предложения.")
        }
        result.append("\nПодтверждено вручную: ").append(compared).append(" из ").append(stores.size)
        if (unverifiedCount > 0) result.append("\nНе подтверждённые цены исключены: ").append(unverifiedCount)
        result.append("\nПроверь наличие, регион, доставку и условия скидки перед покупкой.")
        summary.text = result.toString()
        persistCurrentState()
    }

    private fun clearPrices() {
        priceFields.values.forEach { it.setText("") }
        scanTimes.keys.toList().forEach { key -> scanTimes[key] = 0L }
        verifiedTimes.keys.toList().forEach { key -> verifiedTimes[key] = 0L }
        scanStatusViews.values.forEach { it.text = "Автоматическое считывание не выполнено" }
        verificationStatusViews.values.forEach { it.text = "Не подтверждено вручную. Цена не участвует в расчёте." }
        summary.text = "Цены и подтверждения очищены. Ссылки на карточки и поисковый запрос сохранены."
        persistCurrentState()
    }

    private fun persistCurrentState() {
        if (currentQuery.isBlank() || priceFields.isEmpty()) return
        val state = JSONObject()
        stores.forEach { store ->
            state.put("price_" + store.id, priceFields[store.id]?.text?.toString().orEmpty())
            state.put("url_" + store.id, productLinkFields[store.id]?.text?.toString().orEmpty())
            state.put("scan_time_" + store.id, scanTimes[store.id] ?: 0L)
            state.put("verified_time_" + store.id, verifiedTimes[store.id] ?: 0L)
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

    private fun openStoreSearch(store: Store, query: String) {
        val intent = Intent(this, StoreSearchActivity::class.java).apply {
            putExtra(StoreSearchActivity.EXTRA_STORE_ID, store.id)
            putExtra(StoreSearchActivity.EXTRA_STORE_NAME, store.name)
            putExtra(StoreSearchActivity.EXTRA_SEARCH_URL, store.searchUrl)
            putExtra(StoreSearchActivity.EXTRA_QUERY, query)
        }
        startActivityForResult(intent, 1201)
    }


    @Suppress("DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 1201 || resultCode != RESULT_OK) return
        val raw = data?.getStringExtra(StoreSearchActivity.EXTRA_SELECTED_OFFER) ?: return
        try {
            val offer = JSONObject(raw)
            val storeId = offer.optString("store_id")
            val price = offer.optDouble("price", 0.0)
            val url = offer.optString("url")
            val store = stores.firstOrNull { it.id == storeId }
            if (price <= 0 || store == null || !isStoreProductUrl(store, url)) {
                toast("Выбранная карточка не содержит корректной цены или HTTPS-ссылки на магазин")
                return
            }
            priceFields[storeId]?.setText(formatPrice(price).replace(" ", "").replace(" ", ""))
            productLinkFields[storeId]?.setText(url)
            val scannedAt = offer.optLong("scan_time", System.currentTimeMillis())
            scanTimes[storeId] = scannedAt
            verifiedTimes[storeId] = 0L
            scanStatusViews[storeId]?.text = "Считано со страницы: " + formatScanTime(scannedAt) + " · предварительно"
            verificationStatusViews[storeId]?.text = "Не подтверждено вручную. Цена не участвует в расчёте"
            summary.text = "Добавлено предварительное предложение " + offer.optString("store_name") + ": " + formatPrice(price) + " ₽. Проверь цену, наличие и регион в карточке товара перед сравнением."
            persistCurrentState()
            toast("Предварительная цена добавлена. Проверь карточку товара.")
        } catch (_: Exception) {
            toast("Не удалось импортировать выбранное предложение")
        }
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

    private fun parsePrice(raw: String): Double? {
        // Russian sites often use a narrow no-break space (U+202F) as a thousands separator.
        val normalized = raw.replace(Regex("[\\s\\u00A0\\u202F]"), "").replace(",", ".")
        val value = normalized.toDoubleOrNull()
        return value?.takeIf { it.isFinite() && it > 0.0 }
    }

    private fun invalidateVerification(storeId: String) {
        if ((verifiedTimes[storeId] ?: 0L) > 0L) {
            verifiedTimes[storeId] = 0L
            verificationStatusViews[storeId]?.text = "Цена или ссылка изменена. Подтверди заново."
        }
    }

    private fun isStoreProductUrl(store: Store, value: String): Boolean {
        val uri = try { Uri.parse(value) } catch (_: Exception) { return false }
        val host = uri.host?.lowercase(Locale.ROOT) ?: return false
        if (uri.scheme != "https" || !(host == store.domain || host.endsWith("." + store.domain))) return false
        val parts = uri.path.orEmpty().split('/').filter { it.isNotBlank() }
        if (parts.size < 2) return false
        return when (store.id) {
            "dns" -> parts[0] == "product"
            "mvideo" -> parts[0] == "products" || parts[0] == "product"
            "ozon" -> parts[0] == "product"
            "wb" -> parts[0] == "catalog" && parts[1].toLongOrNull() != null && parts[1] != "0" &&
                (parts.size == 2 || (parts.size == 3 && parts[2].equals("detail.aspx", ignoreCase = true)))
            "ym" -> parts[0].startsWith("product--") || parts[0] == "card" || parts[0] == "product"
            else -> false
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


    private fun formatScanTime(value: Long): String =
        SimpleDateFormat("dd.MM.yyyy HH:mm", Locale("ru", "RU")).format(Date(value))

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
