## Mock Payment Service

This folder provides a lightweight mock payment page that simulates the Payment Service for end-to-end testing of your payment plugin—no real transactions required. It’s ideal for validating payment flows in development and CI environments.

### Getting Started

1. Open `index.html` and update the JB Manager API URL on line 93 to point at your target endpoint.  
2. From the project root, run:
   ```bash
   python -m http.server
   ```