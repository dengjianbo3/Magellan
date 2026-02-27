package com.magellan.ai;

import com.getcapacitor.BridgeActivity;
import java.net.URI;
import java.net.URISyntaxException;

public class MainActivity extends BridgeActivity {
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

    @Override
    public void onBackPressed() {
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

        // No in-app navigation history: move app to background instead of closing.
        moveTaskToBack(true);
    }
}
