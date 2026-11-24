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
            text = "Важно: приложение не подставляет придуманные цены. Открой поиск магазина, проверь карточку товара и наличие в указанном городе, затем внеси фактическую цену и ссылку. Автоматическое получение цен подключается только через разрешённые API или фиды."
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
        summary.text = "Цены очищены. Ссылки на карточки и поисковый запрос сохранены."
        persistCurrentState()
    }

    private fun persistCurrentState() {
        if (currentQuery.isBlank() || priceFields.isEmpty()) return
        val state = JSONObject()
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
            singleLine = true
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
