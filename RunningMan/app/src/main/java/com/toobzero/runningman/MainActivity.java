package com.toobzero.runningman;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import android.webkit.WebSettings;
import android.view.View;
import android.view.WindowManager;

public class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        WebView view = new WebView(this);
        view.setBackgroundColor(0xffded8cb);
        view.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        WebSettings settings = view.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setLoadsImagesAutomatically(true);
        view.setWebChromeClient(new WebChromeClient());
        view.setOverScrollMode(View.OVER_SCROLL_NEVER);
        setContentView(view);
        view.loadUrl("file:///android_asset/index.html");
    }
    @Override public void onBackPressed() { }
}
