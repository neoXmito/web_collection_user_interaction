import cv2
import numpy as np
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tensorflow.keras.models import load_model
import joblib
from ultralytics import YOLO

class CaptchaSolver:
    def __init__(self, num_attempts=5):
        self.num_attempts = num_attempts
        self.driver = webdriver.Chrome()
        self.yolo_model = YOLO("models/yolo_model2/best.pt")
        self.cnn_model = load_model("models/FINALMODELS/captchasolve.h5")
        self.label_encoder = joblib.load('models/trained_label_encoder.pkl')
        self.url = 'http://localhost:5000'  # Update with your URL

    def check_letter_tarakom(self, pic):
        _, pic = cv2.threshold(pic, 127, 255, cv2.THRESH_BINARY)
        s = 90 - (np.sum(pic , axis=0 , keepdims=True) / 255)
        total = len(s[0])
        howmanyblack = sum(1 for i in s[0] if np.sum(i) >= 175)
        return total - howmanyblack <= 22

    def process_captcha(self, image_path):
        image = cv2.imread(image_path)
        results = self.yolo_model(image_path)
        detections = sorted(results[0].boxes, key=lambda box: box.xyxy[0][0])
        
        letters = []
        last_coords = []
        howmany = 0
        
        for box in detections:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            if last_coords:
                if x1 - last_coords[0] > 10:
                    letter_crop = image[y1:y2, x1:x2]
                    resized = cv2.resize(letter_crop, (32, 52))
                    resized = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                    
                    if howmany == 8 and self.check_letter_tarakom(letter_crop):
                        _, binarized = cv2.threshold(resized, 128, 255, cv2.THRESH_BINARY)
                        letters.append(binarized)
                    elif howmany <= 7:
                        _, binarized = cv2.threshold(resized, 128, 255, cv2.THRESH_BINARY)
                        letters.append(binarized)
                    
                    last_coords = [x1, y1, x2, y2]
                    howmany += 1
            else:
                letter_crop = image[y1:y2, x1:x2]
                resized = cv2.resize(letter_crop, (32, 52))
                resized = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                
                if self.check_letter_tarakom(letter_crop):
                    _, binarized = cv2.threshold(resized, 128, 255, cv2.THRESH_BINARY)
                    letters.append(binarized)
                
                last_coords = [x1, y1, x2, y2]
                howmany += 1
        
        predictions = []
        for letter in letters:
            processed = np.array(letter).reshape(1, 52, 32, 1)
            pred = self.cnn_model.predict(processed)
            predicted_char = self.label_encoder.inverse_transform([pred.argmax()])[0]
            predictions.append(predicted_char)
        
        return ''.join(predictions)

    def solve_and_submit(self):
        # Save CAPTCHA image
        captcha_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'captcha-image')))
        captcha_element.screenshot('temp_captcha.png')
        
        # Process image
        prediction = self.process_captcha('temp_captcha.png')
        os.remove('temp_captcha.png')  # Clean up
        
        # Find and fill input field
        input_field = self.driver.find_element(By.ID, 'user-input')
        input_field.clear()
        input_field.send_keys(prediction)
        
        # Submit
        submit_btn = self.driver.find_element(By.ID, 'submit-btn')
        submit_btn.click()
        time.sleep(2)  # Wait for result

    def run(self):
        self.driver.get(self.url)
        
        for attempt in range(self.num_attempts):
            try:
                # Start test
                start_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, 'start-test')))
                start_btn.click()
                
                # Wait for CAPTCHA to load
                time.sleep(1)
                
                # Solve and submit
                self.solve_and_submit()
                
                # Handle result
                if "success" in self.driver.page_source.lower():
                    print(f"Attempt {attempt+1}: Success!")
                else:
                    print(f"Attempt {attempt+1}: Failed")
                
                # Reset for next attempt
                self.driver.refresh()
                time.sleep(1)
                
            except Exception as e:
                print(f"Attempt {attempt+1} failed with error: {str(e)}")
                self.driver.save_screenshot(f'error_{attempt+1}.png')
        
        self.driver.quit()

if __name__ == '__main__':
    # Configure number of attempts here
    bot = CaptchaSolver(num_attempts=10)
    bot.run()