/* --------------------------------------------------------------

   ------------------------------------------------------------ */

const uint8_t  PEDAL_PIN   = A0;      // physical DAC pin
const uint16_t DAC_RES      = 12;     // UNO-R4: 0-4095 counts
const float    V_SUPPLY     = 4.73;   // UNO-R4 Minima reference
const float    V_MIN        = 1.10;   // safety limits
const float    V_MAX        = 4.4;
const uint32_t TIMEOUT_MS   = 300;    // 0.3 s watchdog

// helper -–––––––––––––––––––––––––––––––––––––––––––––––––––––––
inline uint16_t voltsToDac(float v)
{
  v = constrain(v, V_MIN, V_MAX);
  return (uint16_t)round(v / V_SUPPLY * ((1UL << DAC_RES) - 1));
}

// globals
uint32_t   lastRxMs   = 0;
float      lastVolts  = V_MIN;
String     inBuf;

void setup()
{
  Serial.begin(115200);
  analogWriteResolution(DAC_RES);            // 0-4095
  analogWrite(PEDAL_PIN, voltsToDac(V_MIN)); // idle at power-up
  lastRxMs = millis();
}

void loop()
{
  // ----------- non-blocking line reader -----------------------
  while (Serial.available())
  {
    char c = Serial.read();
    if (c == '\n')                     // end of line
    {
      float v = inBuf.toFloat();       // toFloat() returns 0.0 on error
      if (inBuf.length() > 0)          // ignore spurious empty lines
      {
        if (v < V_MIN || v > V_MAX)    // clip, never trust the host
          v = constrain(v, V_MIN, V_MAX);

        analogWrite(PEDAL_PIN, voltsToDac(v));
        lastVolts = v;
        lastRxMs  = millis();
      }
      inBuf = "";
    }
    else if (isPrintable(c) || c == '.' || c == '-')  // keep only legal chars
    {
      inBuf += c;
    }
  }

  // ----------- watchdog - revert to idle ----------------------
  if (millis() - lastRxMs > TIMEOUT_MS && lastVolts != V_MIN)
  {
    analogWrite(PEDAL_PIN, voltsToDac(V_MIN));
    lastVolts = V_MIN;
  }
}
