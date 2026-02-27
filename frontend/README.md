# Frontend (Vue 3 + Vite)

## Development

```bash
npm run dev
```

## Production Build

```bash
npm run build
```

## Android App (Capacitor)

1. Install Capacitor dependencies:

```bash
npm install @capacitor/core @capacitor/cli @capacitor/android
```

2. Build and sync web assets to Android project:

```bash
npm run android:build-web
```

This uses `vite --mode android` and reads `frontend/.env.android`.

3. Run environment preflight:

```bash
npm run android:preflight
```

4. Open Android Studio:

```bash
npm run android:open
```

5. Build debug APK (CLI):

```bash
npm run android:apk:debug
```

More details: `../docs/ANDROID_APP_CAPACITOR_GUIDE.md`
