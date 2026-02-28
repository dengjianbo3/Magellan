package com.magellan.ai;

import com.getcapacitor.BridgeActivity;
import android.os.Bundle;
import android.widget.Toast;
import androidx.activity.OnBackPressedCallback;
import java.net.URI;
import java.net.URISyntaxException;

public class MainActivity extends BridgeActivity {
    private static final long EXIT_CONFIRM_WINDOW_MS = 1800L;
    private long lastBackPressedAt = 0L;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Use dispatcher callback to handle both button and gesture back on modern Android.
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                handleAppBack();
            }
        });
    }

    private boolean isRootPath(String url) {
        if (url == null || url.isEmpty()) {
            return true;
        }
        try {
            URI uri = new URI(url);
            String path = uri.getPath();
            return path == null || path.isEmpty() || "/".equals(path);
        } catch (URISyntaxException ignored) {
            return false;
        }
    }

    private String resolveOrigin(String url) {
        if (url == null || url.isEmpty()) return "";
        try {
            URI uri = new URI(url);
            String scheme = uri.getScheme();
            String authority = uri.getRawAuthority();
            if (scheme == null || authority == null) return "";
            return scheme + "://" + authority;
        } catch (URISyntaxException ignored) {
            return "";
        }
    }

    private void handleAppBack() {
        if (bridge != null && bridge.getWebView() != null && bridge.getWebView().canGoBack()) {
            bridge.getWebView().goBack();
            return;
        }

        if (bridge != null && bridge.getWebView() != null) {
            String currentUrl = bridge.getWebView().getUrl();
            if (!isRootPath(currentUrl)) {
                String origin = resolveOrigin(currentUrl);
                if (!origin.isEmpty()) {
                    bridge.getWebView().loadUrl(origin + "/");
                } else {
                    bridge.getWebView().loadUrl("/");
                }
                return;
            }
        }

        // At root page: require a second back action to move app to background.
        long now = System.currentTimeMillis();
        if (now - lastBackPressedAt < EXIT_CONFIRM_WINDOW_MS) {
            moveTaskToBack(true);
            return;
        }

        lastBackPressedAt = now;
        Toast.makeText(this, "再滑一次返回才会退出应用", Toast.LENGTH_SHORT).show();
    }
}
