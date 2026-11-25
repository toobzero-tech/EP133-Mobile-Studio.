package com.toobzero.priceradar

import android.net.Uri
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

data class YandexMarketOffer(
    val title: String?,
    val priceRub: Long,
    val stockAmount: Long?,
    val fetchedAt: Long
)

/**
 * Uses the official Yandex Market Referral Program API.
 * It resolves a user-shared product URL; it does not search the public catalog.
 */
object YandexMarketAffiliateClient {
    private const val ENDPOINT =
        "https://api.content.market.yandex.ru/v3/affiliate/partner/link/create"

    fun fetchProduct(productUrl: String, oauthToken: String, placeId: String): YandexMarketOffer {
        val parsed = Uri.parse(productUrl)
        val host = parsed.host?.lowercase().orEmpty()
        val isMarketUrl = host == "market.yandex.ru" ||
            host.endsWith(".market.yandex.ru") ||
            host == "market.yandex.com" ||
            host.endsWith(".market.yandex.com")
        require(parsed.scheme == "https" && isMarketUrl) {
            "Нужна HTTPS-ссылка на конкретный товар Яндекс Маркета"
        }
        require(oauthToken.isNotBlank()) { "Не задан OAuth-токен Яндекс Маркета" }
        require(placeId.toLongOrNull()?.let { it > 0L } == true) {
            "Укажи числовой place_id из кабинета реферальной программы"
        }

        val requestUri = Uri.parse(ENDPOINT).buildUpon()
            .appendQueryParameter("url", productUrl)
            .appendQueryParameter("place_id", placeId)
            .appendQueryParameter("format", "json")
            .build()

        val connection = (URL(requestUri.toString()).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 12_000
            readTimeout = 12_000
            instanceFollowRedirects = true
            setRequestProperty("Authorization", "OAuth $oauthToken")
            setRequestProperty("Accept", "application/json")
            setRequestProperty("User-Agent", "PRICE-RADAR-Android/1.2.0")
        }

        try {
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val body = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (code !in 200..299) {
                val apiMessage = try {
                    JSONObject(body).optJSONArray("errors")
                        ?.optJSONObject(0)?.optString("message")
                } catch (_: Exception) {
                    null
                }
                throw IOException("HTTP $code: " + apiMessage?.takeIf { it.isNotBlank() }.orEmpty()
                    .ifBlank { "ошибка API Яндекс Маркета" })
            }

            val json = JSONObject(body)
            if (json.optString("status") != "OK") {
                throw IOException("Яндекс Маркет не подтвердил получение цены")
            }
            val price = json.optLong("price", 0L)
            if (price <= 0L) {
                throw IOException("API не вернул действительную цену товара")
            }
            val stock = if (json.has("stockAmount") && !json.isNull("stockAmount")) {
                json.optLong("stockAmount")
            } else {
                null
            }
            val title = json.optString("title").takeIf { it.isNotBlank() }

            return YandexMarketOffer(
                title = title,
                priceRub = price,
                stockAmount = stock,
                fetchedAt = System.currentTimeMillis()
            )
        } finally {
            connection.disconnect()
        }
    }
}
