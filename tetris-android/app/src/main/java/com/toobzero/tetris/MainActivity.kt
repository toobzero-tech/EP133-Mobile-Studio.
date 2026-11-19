package com.toobzero.tetris
import android.app.Activity
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
class MainActivity : Activity() {
 override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); window.statusBarColor=android.graphics.Color.rgb(17,19,24); window.navigationBarColor=android.graphics.Color.rgb(17,19,24); val web=WebView(this); web.settings.javaScriptEnabled=true; web.settings.domStorageEnabled=true; web.webViewClient=WebViewClient(); web.setBackgroundColor(android.graphics.Color.rgb(17,19,24)); setContentView(web); web.loadUrl("file:///android_asset/index.html") }
}
