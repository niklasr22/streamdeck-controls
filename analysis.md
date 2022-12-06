# Streamdeck USB traffic analysis

## Streamdeck Original Software Commands

Length of 32 bytes
Ends often with 

```
0x61 0xc0 0x24 0x01 0x00 0x00 0x00
```

### Set Brightness

```
0x03 0x08 [brightness as percentage (1B)] 0x6b 0x01
```

### Set Standby Timeout

```
never:  0x03 0x0d 0x00 0x00
5min:   0x03 0x0d 0x2c 0x01
15min:  0x03 0x0d 0x84 0x03
30min:  0x03 0x0d 0x08 0x07
1h:     0x03 0x0d 0x10 0x0e
2h:     0x03 0x0d 0x20 0x1c

cmd:    0x03 0x0d [timeout in secs (2B le)]
```

### Set rotation

1. Sends brightness cmd
2. Sends standby cmd
3. Sends standby cmd again?

### Set image

```
0x02 0x07 [key index (1B)] [is last package (1B)] [body length (2B le)] [package index (2B le)] [image as JPEG max. 1016B]
total length 1024B
```


## Streamdeck Button Handling

- Sends update on any action (key press and release)
- always sends 512 Bytes
- keys begin with an offset of 4 bytes
- 0x01 if key pressed and 0x00 if not pressed
- ordered ltr ttb