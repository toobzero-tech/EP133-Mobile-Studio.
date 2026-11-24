package com.toobzero.priceradar

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.*
import android.graphics.Color
import android.widget.Toast
import java.io.OutputStream

class MainActivity : Activity() {
 private lateinit var web: WebView
 private var chooser: ValueCallback<Array<Uri>>? = null
 private var pendingExport: String? = null
 private var pendingMime: String = "text/csv"
 private var pendingName: String = "price-radar.csv"

 inner class AndroidBridge {
  @JavascriptInterface
  fun saveTextFile(filename: String, mimeType: String, content: String) {
   runOnUiThread {
    pendingName = filename.substringAfterLast('/').ifBlank { "price-radar.csv" }
    pendingMime = mimeType.ifBlank { "text/plain" }
    pendingExport = content
    val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
     addCategory(Intent.CATEGORY_OPENABLE)
     type = pendingMime
     putExtra(Intent.EXTRA_TITLE, pendingName)
    }
    startActivityForResult(intent, 702)
   }
  }
 }

 override fun onCreate(savedInstanceState: Bundle?) {
  super.onCreate(savedInstanceState)
  window.statusBarColor = Color.rgb(17,19,24)
  window.navigationBarColor = Color.rgb(17,19,24)
  web = WebView(this)
  web.setBackgroundColor(Color.rgb(17,19,24))
  web.settings.javaScriptEnabled = true
  web.settings.domStorageEnabled = true
  web.settings.allowFileAccess = true
  web.settings.allowContentAccess = true
  web.addJavascriptInterface(AndroidBridge(), "AndroidBridge")
  web.webViewClient = object : WebViewClient() {
   override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
    val u = request.url
    if (u.scheme == "https" || u.scheme == "http") {
     startActivity(Intent(Intent.ACTION_VIEW, u)); return true
    }
    return false
   }
  }
  web.webChromeClient = object : WebChromeClient() {
   override fun onShowFileChooser(v: WebView, cb: ValueCallback<Array<Uri>>, p: FileChooserParams): Boolean {
    chooser?.onReceiveValue(null); chooser = cb
    val i = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
     addCategory(Intent.CATEGORY_OPENABLE); type = "*/*"
     putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("text/csv","application/json","text/plain"))
    }
    startActivityForResult(i, 701); return true
   }
  }
  setContentView(web)
  if (savedInstanceState == null) web.loadUrl("file:///android_asset/index.html") else web.restoreState(savedInstanceState)
 }

 @Deprecated("Deprecated in Java")
 override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
  super.onActivityResult(requestCode,resultCode,data)
  if (requestCode == 701) {
   val u = if (resultCode == RESULT_OK) data?.data else null
   chooser?.onReceiveValue(if (u != null) arrayOf(u) else null); chooser = null
  } else if (requestCode == 702) {
   val uri = if (resultCode == RESULT_OK) data?.data else null
   val content = pendingExport
   pendingExport = null
   if (uri != null && content != null) {
    try {
     contentResolver.openOutputStream(uri)?.use { it.write(content.toByteArray(Charsets.UTF_8)) }
     Toast.makeText(this, "Файл сохранён", Toast.LENGTH_SHORT).show()
    } catch (e: Exception) {
     Toast.makeText(this, "Не удалось сохранить файл", Toast.LENGTH_LONG).show()
    }
   }
  }
 }

 override fun onSaveInstanceState(out: Bundle) { web.saveState(out); super.onSaveInstanceState(out) }
 @Deprecated("Deprecated in Java")
 override fun onBackPressed() { if (::web.isInitialized && web.canGoBack()) web.goBack() else super.onBackPressed() }
 override fun onDestroy() { if (::web.isInitialized) web.destroy(); super.onDestroy() }
}
