// RetSol LS-450A + Arduino Uno + USB Host Shield
#include <hidboot.h>
#include <usbhub.h>

USB     Usb;
HIDBoot<USB_HID_PROTOCOL_KEYBOARD>    HidKeyboard(&Usb);

class KbdRptParser : public KeyboardReportParser
{
  protected:
    void OnKeyDown(uint8_t mod, uint8_t key);
};

void KbdRptParser::OnKeyDown(uint8_t mod, uint8_t key)
{
  uint8_t c = OemToAscii(mod, key);
  if (c) {
    if (c == '\r') {           // Enter key = end of barcode
      Serial.println();        // Send newline to Python
    } else {
      Serial.write(c);
    }
  }
}

KbdRptParser Prs;

void setup() {
  Serial.begin(9600);
  
  // Use the built-in LED (Pin 13)
  pinMode(LED_BUILTIN, OUTPUT); 
  digitalWrite(LED_BUILTIN, LOW); // Start OFF

  while (!Serial); 
  if (Usb.Init() == -1) {
    Serial.println("USB Host Shield failed!");
    while (1); 
  }
  
  HidKeyboard.SetReportParser(0, &Prs);
  Serial.println("RetSol scanner ready");
}

void loop() {
  Usb.Task();
  // 2. Listen for Python
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim(); 

    if (command == "APPROVED") {
      // SUCCESS: Solid Light for 2 seconds
      digitalWrite(LED_BUILTIN, HIGH);
      delay(2000); 
      digitalWrite(LED_BUILTIN, LOW);
    }
    else if (command == "DENIED") {
      // FAILURE: 3 Fast Blinks
      for (int i=0; i<3; i++) {
        digitalWrite(LED_BUILTIN, HIGH);
        delay(100);
        digitalWrite(LED_BUILTIN, LOW);
        delay(100);
      }
    }
  }
}