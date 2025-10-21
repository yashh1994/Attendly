# Quick Start Guide - Photo Attendance Feature

## Prerequisites

Before using the photo attendance feature, ensure:

1. **Backend Server Running**
   ```bash
   cd Backend
   python run_server.py
   ```

2. **Database Setup**
   - Students must be enrolled in classes
   - Students must have uploaded facial data
   - Teacher account must exist

3. **Mobile App Configuration**
   - Check `lib/services/api_service.dart` baseUrl
   - Default: `http://localhost:5000`
   - For Android Emulator: May need `http://10.0.2.2:5000`

## Camera Permissions

### Android (`android/app/src/main/AndroidManifest.xml`)
Already configured if camera dependency exists:
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-feature android:name="android.hardware.camera" />
<uses-feature android:name="android.hardware.camera.autofocus" />
```

### iOS (`ios/Runner/Info.plist`)
Already configured if camera dependency exists:
```xml
<key>NSCameraUsageDescription</key>
<string>This app needs camera access to take attendance photos</string>
```

## Usage Steps

### For Teachers:

1. **Login as Teacher**
   - Use teacher credentials
   - Navigate to Teacher Home Screen

2. **Select Class**
   - View list of your classes
   - Tap 3-dot menu on class card
   - Select "Take Attendance"

3. **Take Photo**
   - Camera preview loads automatically
   - Position to capture students
   - Tap "Capture Photo"
   - Wait for AI processing (~2-5 seconds)

4. **Review & Adjust**
   - Check recognized students (green with AI badge)
   - Manually toggle any incorrect selections
   - Take additional photos for large classes

5. **Submit**
   - Tap "Submit" in app bar
   - Confirm attendance submission
   - Done! Attendance recorded

## Testing Without Real Students

### Create Test Data:

1. **Create Test Students**
   ```python
   # Use backend API or database
   # Ensure students have facial data uploaded
   ```

2. **Enroll in Test Class**
   ```python
   # Use backend API to enroll students
   ```

3. **Take Test Photo**
   - Use sample classroom photo
   - Or take selfie for single student test

## Troubleshooting

### Camera Not Working
```
Error: Camera failed to initialize
Solution: Check permissions in device settings
```

### Recognition Not Working
```
Error: Recognition failed
Solutions:
1. Check backend server is running
2. Verify API baseUrl is correct
3. Check student facial data exists
4. Review backend logs for errors
```

### No Students Showing
```
Issue: Student list is empty
Solutions:
1. Verify students are enrolled in class
2. Check students have uploaded facial data
3. Use backend API to confirm enrollment
```

### API Errors
```
Error: Failed to load students
Solutions:
1. Check network connectivity
2. Verify backend is accessible
3. Check API token is valid
4. Review backend logs
```

## API Testing

### Test Recognition Endpoint:
```bash
# Backend test script
cd Backend
python test_classroom_recognition.py
```

### Verify Endpoints:
```bash
# Get students with facial data
curl -X GET http://localhost:5000/api/face-data/class/1/students-with-facial-data \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test recognition
curl -X POST http://localhost:5000/api/face-data/recognize-from-photo \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"class_id": 1, "image": "BASE64_IMAGE_DATA"}'
```

## Performance Tips

1. **Photo Quality**
   - Good lighting improves recognition
   - Face camera towards students
   - Avoid extreme angles
   - Keep students within ~5 meters

2. **Large Classes**
   - Take multiple photos from different angles
   - Divide class into sections
   - Use "Take Another Photo" feature

3. **Recognition Accuracy**
   - Default threshold: 0.6 (60%)
   - Lower threshold = more matches but less accuracy
   - Higher threshold = fewer matches but more accuracy

## Development Mode

### Run App:
```bash
cd Frontend/attendly
flutter pub get
flutter run
```

### Hot Reload:
- Press `r` in terminal for hot reload
- Press `R` for hot restart
- Changes to `take_attendance_screen.dart` can be hot reloaded

### Debug Mode:
- Check console logs prefixed with `🔥 FLUTTER:`
- Backend logs show API calls and responses
- Use Flutter DevTools for advanced debugging

## Production Considerations

Before production deployment:

1. **Security**
   - Implement proper token refresh
   - Use HTTPS for API calls
   - Secure camera roll access
   - Encrypt stored images (if caching)

2. **Performance**
   - Optimize image compression
   - Implement request timeout handling
   - Add retry logic for failed requests
   - Cache student list locally

3. **UX Improvements**
   - Add photo preview before submission
   - Implement photo editing (crop, rotate)
   - Add attendance history view
   - Implement offline mode

4. **Error Recovery**
   - Auto-save draft attendance
   - Resume interrupted sessions
   - Sync failed submissions

## Support

For issues or questions:
1. Check `ATTENDANCE_WITH_PHOTO_RECOGNITION.md` for detailed docs
2. Review backend `CLASSROOM_RECOGNITION_API.md`
3. Check backend logs for API errors
4. Review Flutter console for frontend errors
