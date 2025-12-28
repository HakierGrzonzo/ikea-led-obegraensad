#pragma once

#include "PluginManager.h"

class BadApplePlugin : public Plugin
{
private:
  uint8_t frame = 0;
  int frameDelay = 400;

public:
  void setup() override;
  void loop() override;
  const char *getName() const override;
};
