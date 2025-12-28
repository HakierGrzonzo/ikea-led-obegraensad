#include "plugins/BadApplePlugin.h"
#include <vector>

std::vector<std::vector<int>> frames = {
  #include "badApple.h"  
};

void BadApplePlugin::setup()
{
  this->frame = 0;
  if (frames.size() == 0)
  {
    Screen.setPixel(7, 4, 1);
    Screen.setPixel(8, 4, 1);
    Screen.setPixel(7, 5, 1);
    Screen.setPixel(8, 5, 1);
    Screen.setPixel(7, 6, 1);
    Screen.setPixel(8, 6, 1);
    Screen.setPixel(7, 7, 1);
    Screen.setPixel(8, 7, 1);
    Screen.setPixel(7, 8, 1);
    Screen.setPixel(8, 8, 1);

    Screen.setPixel(7, 10, 1);
    Screen.setPixel(8, 10, 1);
    Screen.setPixel(7, 11, 1);
    Screen.setPixel(8, 11, 1);
  }
}

void BadApplePlugin::loop()
{
  int size = std::size(frames);

  if (size > 0)
  {
    std::vector<int> bits = Screen.readBytes(frames[this->frame]);

    for (int i = 0; i < bits.size(); i++)
    {
      Screen.setPixelAtIndex(i, bits[i]);
    }

    this->frame++;

    if (this->frame >= size)
    {
      this->frame = 0;
    }

    auto const frameDelay = 64;
#ifdef ESP32
    vTaskDelay(pdMS_TO_TICKS(frameDelay));
#else
    delay(frameDelay);
#endif
  }
}

const char *BadApplePlugin::getName() const
{
  return "BadApple";
}
