package com.toobzero.priceradar

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.*
import android.graphics.Color
import android.widget.Toast

class MainActivity : Activity() {
 private lateinit var web: WebView
 private var chooser: ValueCallback<Array<Uri>>? = null
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
  }
 }
 override fun onSaveInstanceState(out: Bundle) { web.saveState(out); super.onSaveInstanceState(out) }
 @Deprecated("Deprecated in Java")
 override fun onBackPressed() { if (::web.isInitialized && web.canGoBack()) web.goBack() else super.onBackPressed() }
 override fun onDestroy() { if (::web.isInitialized) web.destroy(); super.onDestroy() }
}
