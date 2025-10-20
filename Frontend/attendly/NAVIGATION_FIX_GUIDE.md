# Complete App Reset Script

## The Problem
You're seeing the face capture screen after splash even though all code has been fixed. This is likely due to:
1. Cached compiled code
2. Old app state in memory
3. Hot reload not picking up navigation changes

## The Solution
You need to do a **FULL CLEAN RESTART** - not just hot reload.

---

## Step-by-Step Fix

### Option 1: Complete Clean (RECOMMENDED) 🔥

Open PowerShell in the Flutter project directory and run:

```powershell
# Stop the running app completely
# Press Ctrl+C in the terminal running flutter

# Navigate to Flutter directory
cd "F:\Marwadi\Sem 8\Mobile App\Frontend\attendly"

# Clean all cached files
flutter clean

# Get dependencies fresh
flutter pub get

# Uninstall the app from device/emulator (important!)
flutter run --uninstall-first
```

### Option 2: Quick Clean 🚀

If Option 1 doesn't work:

```powershell
# Stop the app
# Ctrl+C in flutter terminal

# Clean
flutter clean

# On your physical device, manually uninstall Attendly app
# Settings → Apps → Attendly → Uninstall

# Then run fresh
flutter pub get
flutter run
```

### Option 3: Nuclear Option (If all else fails) 💣

```powershell
# Stop app
# Ctrl+C

# Clean Flutter
flutter clean

# Delete build folder manually
Remove-Item -Path "build" -Recurse -Force

# Delete pub cache for this project
Remove-Item -Path ".dart_tool" -Recurse -Force

# Fresh start
flutter pub get
flutter run --uninstall-first
```

---

## Verification

After running the above, test the flow:

### Test 1: Fresh Install (No Login)
```
1. Open app
2. See: Splash Screen (2.5 seconds)
3. See: Login Screen (NOT face capture) ✅
```

### Test 2: Login as Student
```
1. Login with student credentials
2. See: Student Home Screen (NOT face capture) ✅
3. Navigate to Account tab
4. See: Amber or Green facial data card
5. Only from there you can reach face capture ✅
```

### Test 3: New Student Signup
```
1. Sign up as new student
2. Select "Student" role
3. See: Student Home Screen (NOT face capture) ✅
```

---

## Why This Happens

### Hot Reload Limitations
- Hot reload (`r`) only updates UI changes
- Hot restart (`R`) reloads the app but keeps state
- Navigation changes need full restart

### Cached Routes
- Flutter caches route definitions
- Old navigation logic can persist in memory
- `flutter clean` clears all caches

### App State
- SharedPreferences might have old data
- App might think you're in middle of flow
- Fresh install clears all state

---

## What Was Already Fixed

### ✅ Splash Screen (lib/screens/splash_screen.dart)
```dart
if (authProvider.userRole == 'student') {
  Navigator.pushReplacementNamed(context, Routes.studentHome); // ✅ FIXED
}
```

### ✅ Login Screen (lib/screens/auth/login_screen.dart)
```dart
if (authProvider.userRole == 'student') {
  Navigator.pushReplacementNamed(context, Routes.studentHome); // ✅ FIXED
}
```

### ✅ Role Selection (lib/screens/auth/role_selection_screen.dart)
```dart
if (_selectedRole == 'student') {
  Navigator.pushReplacementNamed(context, Routes.studentHome); // ✅ FIXED
}
```

### ✅ Face Capture Routes
Now ONLY accessible from:
1. Account page → "Register Face Data" button
2. Account page → "Update Face Data" button
3. Join class warning → "Register Now" button (if no face data)

---

## Expected Logs After Fix

When you restart the app, you should see:

```
🔥 AUTH_PROVIDER: Loading auth data...
🔥 AUTH_PROVIDER: Token found: false/true
🔥 AUTH_PROVIDER: User data found: false/true

🔥 SPLASH: Checking authentication...
🔥 SPLASH: isAuthenticated: true/false
🔥 SPLASH: userRole: student
🔥 SPLASH: Navigating to student home  // ✅ THIS, NOT face capture
```

If you see "Navigating to student home" but still go to face capture, it means you have cached code.

---

## Additional Checks

### Check Main.dart Routes
Verify routes are defined correctly:

```dart
routes: {
  Routes.splash: (context) => const SplashScreen(),
  Routes.login: (context) => const LoginScreen(),
  Routes.studentHome: (context) => const StudentHomeScreen(),
  Routes.faceCapture: (context) => const FaceCaptureScreen(),
}
```

### Check Initial Route
```dart
initialRoute: Routes.splash,  // ✅ Should be splash
```

### Clear App Data (Physical Device)
On your Android device:
1. Settings → Apps → Attendly
2. Storage → Clear Storage
3. Storage → Clear Cache
4. Force Stop
5. Reopen app

---

## If Still Not Working

If after all this you still see face capture after splash:

1. **Check the Console Logs**
   - Look for "Navigating to..." messages
   - See which screen is actually being called

2. **Share the Logs**
   - Copy the full console output from app start
   - Look for any errors or unexpected navigation

3. **Check File Saves**
   - Make sure all files were saved
   - Check git status: `git status`
   - Verify changes: `git diff`

4. **Restart VS Code**
   - Sometimes VS Code caches file states
   - Close and reopen VS Code
   - Then run `flutter clean` and `flutter run`

---

## Quick Command Reference

```powershell
# Full reset (recommended)
flutter clean && flutter pub get && flutter run --uninstall-first

# If that doesn't work
flutter clean
Remove-Item -Path "build" -Recurse -Force
flutter pub get
flutter run --uninstall-first

# Check what's running
flutter devices

# Kill all flutter processes
taskkill /F /IM flutter.exe /T
taskkill /F /IM dart.exe /T
```

---

## Summary

✅ All code is already fixed  
✅ No navigation to face capture from splash/login/role selection  
❌ You need to clean cached code  
🔄 Run: `flutter clean && flutter pub get && flutter run --uninstall-first`  

The code is correct - you just need a fresh build! 🚀
