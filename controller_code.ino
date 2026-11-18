const uint8_t  PEDAL_PIN   = A0;     
const uint16_t DAC_RES     = 12;     
const float    V_SUPPLY    = 4.73;   
const float    V_MIN       = 1.10;   
const float    V_MAX       = 4.40;
const float    V_FALLBACK  = 1.90;   // Voltage after timeout
const uint32_t TIMEOUT_MS  = 1000;   // 1 second watchdog

// Convert voltage to DAC value
inline uint16_t voltsToDac(float v)
{
  v = constrain(v, V_MIN, V_MAX);
  return (uint16_t)round(
    v / V_SUPPLY * ((1UL << DAC_RES) - 1)
  );
}

// Global variables
uint32_t lastRxMs = 0;
float lastVolts = V_FALLBACK;
String inBuf;

void setup()
{
  Serial.begin(115200);

  analogWriteResolution(DAC_RES);

  // Output 1.90 V at startup
  analogWrite(PEDAL_PIN, voltsToDac(V_FALLBACK));

  lastRxMs = millis();
}

void loop()
{
  // ----------- Non-blocking serial reader -----------
  while (Serial.available())
  {
    char c = Serial.read();

    if (c == '\n')
    {
      if (inBuf.length() > 0)
      {
        float v = inBuf.toFloat();

        // Keep voltage within allowed limits
        v = constrain(v, V_MIN, V_MAX);

        // Update DAC output
        analogWrite(PEDAL_PIN, voltsToDac(v));

        lastVolts = v;
        lastRxMs = millis();
      }

      inBuf = "";
    }
    else if (isPrintable(c))
    {
      inBuf += c;
    }
  }

  // ----------- 1-second watchdog -----------
  if (millis() - lastRxMs > TIMEOUT_MS &&
      lastVolts != V_FALLBACK)
  {
    // No voltage received for 1 second
    // Return output to 1.90 V
    analogWrite(PEDAL_PIN, voltsToDac(V_FALLBACK));

    lastVolts = V_FALLBACK;
  }
}
