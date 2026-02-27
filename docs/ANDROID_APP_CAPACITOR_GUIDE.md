# Android App (Capacitor) 接入指南

本指南基于当前 `frontend`（Vue + Vite）项目，目标是快速产出安卓安装包。

## 1. 前置条件
- Node.js 18+
- Android Studio（含 Android SDK）
- Java 17（建议）

## 2. 安装 Capacitor 依赖
在仓库根目录执行：

```bash
npm --prefix frontend install @capacitor/core @capacitor/cli @capacitor/android
```

## 3. 运行环境自检（推荐先执行）

```bash
npm --prefix frontend run android:preflight
```

如果这里提示 Java/Gradle 不可用，先修复环境再继续。

## 4. 构建并同步 Web 资源（推荐）

```bash
npm --prefix frontend run android:build-web
```

该命令会自动执行：
- `vite build`
- 清理 `dist` 中 `.gz/.br` 压缩旁路文件（避免 Android assets 重名冲突）
- `cap sync android`

默认会使用 `frontend/.env.android`（`vite --mode android`）进行打包配置。

## 5. 初始化 Capacitor（首次）

```bash
cd frontend
npx cap init Magellan com.magellan.ai --web-dir=dist
```

如果你已存在 `capacitor.config.json`（当前仓库已提供），可跳过这一步。

## 6. 添加 Android 平台（首次）

```bash
cd frontend
npx cap add android
```

## 7. 每次更新前端后的同步

```bash
npm --prefix frontend run android:build-web
```

## 8. 在 Android Studio 中运行/打包

```bash
cd frontend
npx cap open android
```

然后在 Android Studio 中：
- Debug 安装：Run 到真机/模拟器
- Release 包：`Build > Generate Signed Bundle / APK`

也可以直接命令行打 Debug APK：

```bash
npm --prefix frontend run android:apk:debug
```

## 9. 网络与后端联通说明
- 生产建议使用 HTTPS 域名（API + WebSocket）。
- 确保前端配置的 API 地址指向可公网访问的后端。
- WebSocket 需使用 `wss://`。

## 10. 建议的验证清单
- 登录/鉴权是否稳定
- 专家群聊长会话是否正常
- 头脑风暴断线重连与会话恢复
- 图片上传与粘贴（安卓设备差异需要真机验证）

## 11. 图标资源说明
- Web manifest 图标已配置为 PNG：
  - `frontend/public/icons/icon-192.png`
  - `frontend/public/icons/icon-512.png`
  - `frontend/public/icons/apple-touch-icon.png`

## 12. 下一步（可选增强）
- 集成 Capacitor 插件：`@capacitor/share`、`@capacitor/push-notifications`、`@capacitor/filesystem`
- 增加原生级通知和后台提醒
- 接入应用更新机制（Play 内测轨）

## 13. 常见故障排查
- `Unable to locate a Java Runtime`：未安装 JDK 或 `JAVA_HOME` 未配置。
- macOS 可用以下方式安装并配置 JDK17：
  ```bash
  brew install openjdk@17
  echo 'export JAVA_HOME=$(/usr/libexec/java_home -v 17)' >> ~/.zshrc
  echo 'export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.zshrc
  source ~/.zshrc
  ```
- `gradlew` 失败但 Android Studio 能打开：优先在 Android Studio 里安装缺失 SDK/Build Tools。
- WebSocket 在 App 内失败：确认后端地址为 `https/wss` 且证书有效。
- 当前如果后端仅 `http/ws`，需确保 `AndroidManifest.xml` 已设置 `android:usesCleartextTraffic=\"true\"`（本仓库已处理）。
