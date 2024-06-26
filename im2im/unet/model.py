#Modified by Anuj 1st April 2024 #

import torch
import torch.nn as nn
import torch.nn.functional as F


class DoubleConv(nn.Module):
  """(convolution => [BN] => ReLU) * 2"""

  def __init__(self, in_channels, out_channels, mid_channels=None):
    super().__init__()
    if not mid_channels:
      mid_channels = out_channels
    self.double_conv = nn.Sequential(
        nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, bias=False),
        nn.BatchNorm2d(mid_channels),
        nn.ReLU(inplace=True),
        nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True)
    )

  def forward(self, x):
    return self.double_conv(x)


class Down(nn.Module):
  """Downscaling with maxpool then double conv"""

  def __init__(self, in_channels, out_channels):
    super().__init__()
    self.maxpool_conv = nn.Sequential(
        nn.MaxPool2d(2),
        DoubleConv(in_channels, out_channels)
    )

  def forward(self, x):
    return self.maxpool_conv(x)


class AvgDown(nn.Module):
  """Downscaling with average pool then double conv"""

  def __init__(self, in_channels, out_channels):
    super().__init__()
    self.avgpool_conv = nn.Sequential(
        nn.AvgPool2d(2),
        DoubleConv(in_channels, out_channels)
    )

  def forward(self, x):
    return self.avgpool_conv(x)

class Up(nn.Module):
  """Upscaling then double conv"""

  def __init__(self, in_channels, out_channels, bilinear=True):
    super().__init__()

    # if bilinear, use the normal convolutions to reduce the number of channels
    if bilinear:
      self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
      self.conv = DoubleConv(in_channels, out_channels, in_channels // 2)
    else:
      self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
      self.conv = DoubleConv(in_channels, out_channels)

  def forward(self, x1, x2):
    x1 = self.up(x1)
    # input is CHW
    diffY = x2.size()[2] - x1.size()[2]
    diffX = x2.size()[3] - x1.size()[3]
    x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2,
                    diffY // 2, diffY - diffY // 2])
    x = torch.cat([x2, x1], dim=1)
    return self.conv(x)


class OutConv(nn.Module):
  def __init__(self, in_channels, out_channels):
    super(OutConv, self).__init__()
    self.out_conv = nn.Sequential(nn.Conv2d(in_channels, out_channels, kernel_size=1),
                                  nn.Tanh())

  def forward(self, x):
    # return F.softmax(self.conv(x), dim=1)  # normalize class probabilities
    return self.out_conv(x)


class UNet(nn.Module):
  def __init__(self, n_channels, n_classes, bilinear=False):
    super(UNet, self).__init__()
    self.n_channels = n_channels
    self.n_classes = n_classes
    self.bilinear = bilinear

    self.inc = DoubleConv(n_channels, 64)
    self.down1 = Down(64, 128)
    self.down2 = Down(128, 256)
    self.down3 = Down(256, 512)
    factor = 2 if bilinear else 1
    self.down4 = Down(512, 1024 // factor)
    self.up1 = Up(1024, 512 // factor, bilinear)
    self.up2 = Up(512, 256 // factor, bilinear)
    self.up3 = Up(256, 128 // factor, bilinear)
    self.up4 = Up(128, 64, bilinear)
    self.outc = OutConv(64, n_classes)

  def forward(self, x):
    # print(f"input type: {type(x)}")
    x1 = self.inc(x)
    # print(f"x1 type: {type(x1)}")
    x2 = self.down1(x1)
    # print(f"x2 type: {type(x2)}")
    x3 = self.down2(x2)
    # print(f"x3 type: {type(x3)}")
    x4 = self.down3(x3)
    # print(f"x4 type: {type(x4)}")
    x5 = self.down4(x4)
    # print(f"x5 type: {type(x5)}")
    x = self.up1(x5, x4)
    # print(f"x up1 type: {type(x)}")
    x = self.up2(x, x3)
    # print(f"x up2 type: {type(x)}")
    x = self.up3(x, x2)
    # print(f"x up3 type: {type(x)}")
    x = self.up4(x, x1)
    # print(f"x up4 type: {type(x)}")
    logits = self.outc(x)
    # print(f"out type: {type(x)}")
    # print(f"out: {logits}")
    return logits


class AvgPoolUNet(nn.Module):
  def __init__(self, n_channels, n_classes, bilinear=False):
    super(UNet, self).__init__()
    self.n_channels = n_channels
    self.n_classes = n_classes
    self.bilinear = bilinear

    self.inc = DoubleConv(n_channels, 64)
    self.down1 = AvgDown(64, 128)
    self.down2 = AvgDown(128, 256)
    self.down3 = AvgDown(256, 512)
    factor = 2 if bilinear else 1
    self.down4 = AvgDown(512, 1024 // factor)
    self.up1 = Up(1024, 512 // factor, bilinear)
    self.up2 = Up(512, 256 // factor, bilinear)
    self.up3 = Up(256, 128 // factor, bilinear)
    self.up4 = Up(128, 64, bilinear)
    self.outc = OutConv(64, n_classes)

  def forward(self, x):
    # print(f"input type: {type(x)}")
    x1 = self.inc(x)
    # print(f"x1 type: {type(x1)}")
    x2 = self.down1(x1)
    # print(f"x2 type: {type(x2)}")
    x3 = self.down2(x2)
    # print(f"x3 type: {type(x3)}")
    x4 = self.down3(x3)
    # print(f"x4 type: {type(x4)}")
    x5 = self.down4(x4)
    # print(f"x5 type: {type(x5)}")
    x = self.up1(x5, x4)
    # print(f"x up1 type: {type(x)}")
    x = self.up2(x, x3)
    # print(f"x up2 type: {type(x)}")
    x = self.up3(x, x2)
    # print(f"x up3 type: {type(x)}")
    x = self.up4(x, x1)
    # print(f"x up4 type: {type(x)}")
    logits = self.outc(x)
    # print(f"out type: {type(x)}")
    # print(f"out: {logits}")
    return logits


if __name__ == '__main__':
  # test case
  net = AvgPoolUNet(n_channels=1, n_classes=1, bilinear=False)
  test_img = torch.rand((1, 1, 100, 100))
  test_out = net(test_img)
  print(f'test in: {test_img}\ntest out: {test_out}')

