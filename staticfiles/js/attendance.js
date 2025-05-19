document.addEventListener('DOMContentLoaded', function() {
    // Check if CONFIG is available
    if (typeof CONFIG === 'undefined') {
        console.error('Configuration not loaded. Make sure the CONFIG object is defined in your template.');
        return;
    }
    
    // Set CSRF token for all AJAX requests
    const csrftoken = CONFIG.CSRF_TOKEN;
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
    // Elements
    const qrForm = document.getElementById('qr-form');
    const qrCodeInput = document.getElementById('qr-code-input');
    const latitudeInput = document.getElementById('latitude-input');
    const longitudeInput = document.getElementById('longitude-input');
    const biometricDataInput = document.getElementById('biometric-data-input');
    const biometricSection = document.getElementById('biometric-section');
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const feedbackDiv = document.getElementById('biometric-feedback');
    const feedbackMessage = document.getElementById('feedback-message');
    const retryBtn = document.getElementById('retry-btn');
    const locationStatus = document.getElementById('location-status');
    const locationText = document.getElementById('location-text');
    const qrScannerModal = document.getElementById('qr-scanner-modal');
    const closeQrScanner = document.getElementById('close-qr-scanner');
    const qrScanBtns = document.querySelectorAll('.qr-scan-btn');
    
    // State
    let currentQrCode = null;
    let stream = null;
    let faceDetectionInterval = null;
    let modelsLoaded = false;
    
    // Initialize QR Scanner
    function initializeQrScanner() {
        const html5QrCode = new Html5Qrcode("qr-reader");
        
        const qrScanner = new Html5QrcodeScanner(
            "qr-reader",
            { 
                fps: 10,
                qrbox: 250 
            },
            /* verbose= */ false
        );

        qrScanner.render(onScanSuccess, onScanFailure);
    }
    
    // Handle successful QR code scan
    async function onScanSuccess(decodedText, decodedResult) {
        console.log(`QR Code matched = ${decodedText}`, decodedResult);
        currentQrCode = decodedText;
        
        // Hide QR scanner and show biometric verification
        document.getElementById('qr-reader').style.display = 'none';
        
        // Get location and start face detection
        const position = await getCurrentPosition();
        if (position) {
            await startFaceDetection();
        } else {
            showFeedback('Unable to get your location. Please enable location services and try again.', 'error');
        }
    }
    
    // Handle QR scan failure
    function onScanFailure(error) {
        // Handle scan failure
        console.warn(`QR error = ${error}`);
    }
    
    // Get current geolocation
    function getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                showFeedback('Geolocation is not supported by your browser', 'error');
                reject('Geolocation not supported');
                return;
            }
            
            locationStatus.className = 'text-sm px-3 py-1 rounded-full bg-yellow-100 text-yellow-800';
            locationText.textContent = 'Getting location...';
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const { latitude, longitude, accuracy } = position.coords;
                    latitudeInput.value = latitude;
                    longitudeInput.value = longitude;
                    
                    // Update location status
                    locationStatus.className = 'text-sm px-3 py-1 rounded-full bg-green-100 text-green-800';
                    locationText.textContent = `Location found (Accuracy: ${Math.round(accuracy)}m)`;
                    
                    // Reverse geocode to get address
                    const geocoder = new google.maps.Geocoder();
                    const latlng = { lat: parseFloat(latitude), lng: parseFloat(longitude) };
                    
                    geocoder.geocode({ location: latlng }, (results, status) => {
                        if (status === 'OK' && results[0]) {
                            locationText.textContent = results[0].formatted_address;
                        }
                    });
                    
                    resolve(position);
                },
                (error) => {
                    console.error('Error getting location:', error);
                    locationStatus.className = 'text-sm px-3 py-1 rounded-full bg-red-100 text-red-800';
                    
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            locationText.textContent = 'Location access was denied';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            locationText.textContent = 'Location information is unavailable';
                            break;
                        case error.TIMEOUT:
                            locationText.textContent = 'Location request timed out';
                            break;
                        default:
                            locationText.textContent = 'An unknown error occurred';
                    }
                    
                    reject(error);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        });
    }
    
    // Start face detection
    async function startFaceDetection() {
        // Show biometric section
        biometricSection.classList.remove('hidden');
        
        try {
            // Load face-api.js models
            if (!modelsLoaded) {
                showFeedback('Loading face detection models...', 'info');
                await Promise.all([
                    faceapi.nets.tinyFaceDetector.loadFromUri('/static/weights'),
                    faceapi.nets.faceLandmark68Net.loadFromUri('/static/weights'),
                    faceapi.nets.faceRecognitionNet.loadFromUri('/static/weights')
                ]);
                modelsLoaded = true;
            }
            
            // Start video stream
            stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    width: 500, 
                    height: 375,
                    facingMode: 'user' 
                },
                audio: false
            });
            
            video.srcObject = stream;
            
            // Start face detection
            detectFace();
            
        } catch (error) {
            console.error('Error accessing camera:', error);
            showFeedback('Could not access camera. Please ensure you have granted camera permissions.', 'error');
        }
    }
    
    // Detect face in video stream
    function detectFace() {
        faceDetectionInterval = setInterval(async () => {
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                const detections = await faceapi.detectAllFaces(
                    video, 
                    new faceapi.TinyFaceDetectorOptions()
                ).withFaceLandmarks();
                
                // Clear canvas
                const context = canvas.getContext('2d');
                context.clearRect(0, 0, canvas.width, canvas.height);
                
                // Draw detections
                faceapi.draw.drawDetections(canvas, detections);
                faceapi.draw.drawFaceLandmarks(canvas, detections);
                
                // Check if face is detected
                if (detections.length > 0) {
                    // Face detected, proceed with verification
                    clearInterval(faceDetectionInterval);
                    await verifyFace();
                }
            }
        }, 300);
    }
    
    // Verify face and submit attendance
    async function verifyFace() {
        showFeedback('Verifying your identity...', 'info');
        
        try {
            // Capture face data (in a real app, this would be more sophisticated)
            const faceDescriptor = await captureFaceDescriptor();
            
            // Convert descriptor to string for submission
            const faceData = JSON.stringify(faceDescriptor);
            biometricDataInput.value = faceData;
            
            // Submit the form
            const formData = new FormData(qrForm);
            
            const response = await fetch(CONFIG.VERIFY_BIOMETRIC_URL, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': CONFIG.CSRF_TOKEN
                },
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                if (result.verified) {
                    showFeedback('Attendance verified successfully!', 'success');
                    // Redirect or update UI as needed
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    showFeedback('Verification failed. Please try again.', 'error');
                    retryBtn.classList.remove('hidden');
                }
            } else {
                showFeedback(result.error || 'Verification failed. Please try again.', 'error');
                retryBtn.classList.remove('hidden');
            }
            
        } catch (error) {
            console.error('Error during verification:', error);
            showFeedback('An error occurred during verification. Please try again.', 'error');
            retryBtn.classList.remove('hidden');
        }
    }
    
    // Capture face descriptor for verification
    async function captureFaceDescriptor() {
        // In a real app, you would capture and process the face descriptor
        // This is a simplified version
        const detections = await faceapi.detectAllFaces(
            video, 
            new faceapi.TinyFaceDetectorOptions()
        ).withFaceLandmarks().withFaceDescriptors();
        
        if (detections.length > 0) {
            return detections[0].descriptor;
        }
        throw new Error('No face detected');
    }
    
    // Show feedback message
    function showFeedback(message, type = 'info') {
        feedbackDiv.className = `biometric-feedback ${type}`;
        feedbackMessage.textContent = message;
        feedbackDiv.classList.remove('hidden');
    }
    
    // Reset verification process
    function resetVerification() {
        // Stop video stream
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        
        // Clear canvas
        const context = canvas.getContext('2d');
        context.clearRect(0, 0, canvas.width, canvas.height);
        
        // Reset UI
        feedbackDiv.classList.add('hidden');
        retryBtn.classList.add('hidden');
        
        // Reset form
        qrForm.reset();
    }
    
    // Event Listeners
    retryBtn.addEventListener('click', () => {
        resetVerification();
        startFaceDetection();
    });
    
    // Close QR scanner modal
    if (closeQrScanner) {
        closeQrScanner.addEventListener('click', () => {
            qrScannerModal.classList.add('hidden');
            // Reset scanner here if needed
        });
    }
    
    // Handle QR scan buttons
    qrScanBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            currentQrCode = btn.dataset.qrCode;
            qrCodeInput.value = currentQrCode;
            
            // Get location
            try {
                const position = await getCurrentPosition();
                if (position) {
                    qrScannerModal.classList.add('hidden');
                    await startFaceDetection();
                }
            } catch (error) {
                showFeedback('Location access is required for attendance.', 'error');
            }
        });
    });
    
    // Initialize
    initializeQrScanner();
    
    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        if (faceDetectionInterval) {
            clearInterval(faceDetectionInterval);
        }
    });
});
