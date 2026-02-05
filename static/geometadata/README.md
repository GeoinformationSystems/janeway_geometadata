# Geometadata Plugin - Static Assets

This directory contains JavaScript libraries, CSS stylesheets, and images used by
the Geometadata plugin for Janeway.

## Third-Party Libraries

### Leaflet.js

- **Version**: 1.9.4
- **Source**: <https://leafletjs.com/>
- **License**: BSD 2-Clause License
- **Files**:
  - `js/leaflet.js`
  - `css/leaflet.css`
  - `css/images/marker-icon.png`
  - `css/images/marker-icon-2x.png`
  - `css/images/marker-shadow.png`
  - `css/images/layers.png`
  - `css/images/layers-2x.png`

**BSD 2-Clause License**:
```
Copyright (c) 2010-2024, Volodymyr Agafonkin
Copyright (c) 2010-2011, CloudMade
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### Leaflet.draw

- **Version**: 1.0.4
- **Source**: <https://github.com/Leaflet/Leaflet.draw>
- **License**: MIT License
- **Files**:
  - `js/leaflet.draw.js`
  - `css/leaflet.draw.css`
  - `css/images/spritesheet.png`
  - `css/images/spritesheet-2x.png`
  - `css/images/spritesheet.svg`

**MIT License**:

```
The MIT License (MIT)

Copyright (c) 2012-2017 Jacob Toye and Leaflet contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Leaflet.fullscreen

- **Version**: 3.0.2
- **Source**: <https://github.com/brunob/leaflet.fullscreen>
- **License**: MIT License
- **Files**:
  - `js/leaflet.fullscreen.js`
  - `css/leaflet.fullscreen.css`

Provides fullscreen control for Leaflet maps using the browser's native Fullscreen API
with a fallback to pseudo-fullscreen mode for browsers without native support.

**MIT License**:

```
The MIT License (MIT)

Copyright (c) Bruno B.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Leaflet-providers

- **Version**: 2.0.0
- **Source**: <https://github.com/leaflet-extras/leaflet-providers>
- **License**: BSD 2-Clause License
- **Files**:
  - `js/leaflet-providers.js`

Provides easy access to various tile providers (OpenStreetMap, OpenTopoMap, etc.)
for Leaflet maps without requiring manual URL configuration.

**BSD 2-Clause License**:

```
Copyright (c) 2013, Leaflet Providers contributors
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## Custom Files

The following files are custom code for the Geometadata plugin:

- `js/geometadata-display.js` - Map display functionality for article/preprint/issue pages
- `js/geometadata-edit.js` - Map editing with drawing tools for editors
- `css/geometadata.css` - Custom styling for geometadata UI components

These files are licensed under the same license as Janeway (AGPL v3).

## Updating Libraries

To update the third-party libraries:

1. Download new versions from their official sources:
   - Leaflet: <https://leafletjs.com/download.html>
   - Leaflet.draw: <https://github.com/Leaflet/Leaflet.draw/releases>
   - Leaflet.fullscreen: <https://github.com/brunob/leaflet.fullscreen/releases>
   - Leaflet-providers: <https://github.com/leaflet-extras/leaflet-providers/releases>

2. Replace the files in this directory

3. Update this README with the new version numbers

4. Test the plugin to ensure compatibility
