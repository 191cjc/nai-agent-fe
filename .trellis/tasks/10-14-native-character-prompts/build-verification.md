# Clean Web Build Verification

- Stage: `/tmp/nai-native-web-0dni6m8c`
- Inputs: explicit web package/lock/index/TypeScript/Vite files plus src,
  copied into a fresh directory without `.env*` files.
- Environment: only normal PATH/HOME, LANG, explicit empty user/global npm
  config files and HTTPS registry; build adds NAI_WEB_BASE_PATH=/novelai/.
- `npm ci --offline --no-audit --no-fund`: exit 0.
- `npm run build` (TypeScript and Vite): exit 0.
- Source file-map SHA-256:
  `2066d1687d3316fd2d90762b20e70c401af17ff8907ef65353e2087e9b601642`.

| Output | SHA-256 |
| --- | --- |
| `index.html` | `72bc573f0f38238749f8284224f986d4ad669410e673759fcc5213045633fe33` |
| `assets/index-CAQSnE0T.js` | `87e2beb3dbf182217f1352a98bc0df27fc9b8a7c0112fa6a0ad8a0d9d6ef6364` |
| `assets/index-CjMMQhTO.css` | `423889b10010dbea94f09b5d4885079f4bbb456eb67d2825e98e18ee3acd9d4c` |

The source digest must still match the final reviewed/committed inputs before
release. Rebuild if subsequent fixes change these inputs. No frontend
automated tests, browser automation, credentials or paid providers were used.
