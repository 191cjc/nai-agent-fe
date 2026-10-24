function checkCancelled(signal: AbortSignal): void {
  if (signal.aborted) throw new DOMException('Image export cancelled.', 'AbortError')
}

function decodeImage(url: string, signal: AbortSignal): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    function cleanup() {
      image.onload = null
      image.onerror = null
      signal.removeEventListener('abort', abort)
    }
    function abort() {
      cleanup()
      image.removeAttribute('src')
      reject(new DOMException('Image export cancelled.', 'AbortError'))
    }
    image.onload = () => {
      cleanup()
      if (image.naturalWidth && image.naturalHeight) resolve(image)
      else { image.removeAttribute('src'); reject(new Error('Empty image.')) }
    }
    image.onerror = () => {
      cleanup()
      image.removeAttribute('src')
      reject(new Error('Image could not be decoded.'))
    }
    signal.addEventListener('abort', abort, { once: true })
    if (signal.aborted) abort()
    else image.src = url
  })
}

/** Export local NovelAI pixels at their original size, without PNG text or stealth payloads. */
export async function sanitizedPng(url: string, signal: AbortSignal): Promise<Blob> {
  checkCancelled(signal)
  // Decode the viewer-owned Blob URL directly; never fetch provider/server bytes again.
  const image = await decodeImage(url, signal)
  const canvas = document.createElement('canvas')
  try {
    checkCancelled(signal)
    canvas.width = image.naturalWidth
    canvas.height = image.naturalHeight
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Canvas is unavailable.')
    context.drawImage(image, 0, 0)
    {
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height)
      for (let offset = 0; offset < pixels.data.length; offset += 4) {
        // NovelAI stealth metadata can use alpha or RGB least-significant bits.
        // Outputs are opaque: restore alpha and remove all three RGB carriers.
        pixels.data[offset] &= 254
        pixels.data[offset + 1] &= 254
        pixels.data[offset + 2] &= 254
        pixels.data[offset + 3] = 255
      }
      context.putImageData(pixels, 0, 0)
    }
    checkCancelled(signal)
    // A fresh Canvas PNG does not copy the source PNG's ancillary/text chunks.
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(result => {
        if (result && result.type === 'image/png' && result.size) resolve(result)
        else reject(new Error('PNG export failed.'))
      }, 'image/png')
    })
    checkCancelled(signal)
    return blob
  } finally {
    canvas.width = 0
    canvas.height = 0
    image.removeAttribute('src')
  }
}

export function downloadPng(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  try {
    link.href = url
    link.download = filename
    document.body.append(link)
    link.click()
  } finally {
    link.remove()
    // Allow the browser to consume the download before releasing its temporary URL.
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  }
}
