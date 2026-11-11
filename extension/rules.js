// DLP Rules - Whitelist & Magic Byte Verification (Anti-Spoofing)
const DLP_RULES = {
  mode: "whitelist",

  allowedExtensions: [
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    ".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".csv"
  ],

  // Known dangerous/disguised signatures (Even if renamed to .png or .jpg!)
  dangerousSignatures: [
    { name: "Windows Executable (EXE/DLL)", bytes: [0x4D, 0x5A] }, // MZ
    { name: "Rhino 3D Model (.3dm)", bytes: [0x33, 0x44, 0x20, 0x4D, 0x6F, 0x64, 0x65, 0x6C] }, // 3D Model
    { name: "Blender 3D Project", bytes: [0x42, 0x4C, 0x45, 0x4E, 0x44, 0x45, 0x52] }, // BLENDER
    { name: "Kaydara FBX 3D", bytes: [0x4B, 0x61, 0x79, 0x64, 0x61, 0x72, 0x61, 0x20, 0x46, 0x42, 0x58] },
    { name: "glTF Binary 3D", bytes: [0x67, 0x6C, 0x54, 0x46] }, // glTF
    { name: "ZIP Archive", bytes: [0x50, 0x4B, 0x03, 0x04] }, // PK..
    { name: "7-Zip Archive", bytes: [0x37, 0x7A, 0xBC, 0xAF, 0x27, 0x1C] },
    { name: "RAR Archive", bytes: [0x52, 0x61, 0x72, 0x21, 0x1A, 0x07] }
  ],

  // Valid legitimate headers for allowed file types
  validHeaders: {
    ".png": [[0x89, 0x50, 0x4E, 0x47]], // \x89PNG
    ".jpg": [[0xFF, 0xD8, 0xFF]],
    ".jpeg": [[0xFF, 0xD8, 0xFF]],
    ".gif": [[0x47, 0x49, 0x46, 0x38]], // GIF8
    ".pdf": [[0x25, 0x50, 0x44, 0x46]] // %PDF
  },

  checkFilenamePolicy: function (filename) {
    if (!filename) return null;
    const lower = filename.toLowerCase();
    const dotIndex = lower.lastIndexOf('.');
    if (dotIndex === -1) return "Files without extensions are not permitted";

    const ext = lower.substring(dotIndex);
    if (this.mode === "whitelist" && !this.allowedExtensions.includes(ext)) {
      return `File format (${ext}) is not on the corporate approved list.`;
    }
    return null;
  },

  // Inspects true binary content (Catches .exe, .fbx, or .zip renamed to .png/.jpg!)
  inspectBinaryPayload: function (filename, rawBuffer) {
    if (!rawBuffer) return null;
    
    // Normalize ArrayBuffer, Buffer, or Uint8Array
    let uint8;
    if (rawBuffer instanceof Uint8Array) {
      uint8 = rawBuffer;
    } else if (rawBuffer.buffer) {
      uint8 = new Uint8Array(rawBuffer.buffer, rawBuffer.byteOffset || 0, rawBuffer.byteLength || rawBuffer.length);
    } else {
      uint8 = new Uint8Array(rawBuffer);
    }

    if (uint8.length < 2) return null;

    const lower = filename.toLowerCase();
    const ext = lower.substring(lower.lastIndexOf('.'));

    // 1. Check if the file contains any forbidden/dangerous binary headers (EXE, 3D, ZIP)
    for (const sig of this.dangerousSignatures) {
      if (uint8.length >= sig.bytes.length) {
        let match = true;
        for (let i = 0; i < sig.bytes.length; i++) {
          if (uint8[i] !== sig.bytes[i]) {
            match = false;
            break;
          }
        }
        if (match) {
          return `Security Alert: File is actually a disguised [${sig.name}], not a real ${ext}!`;
        }
      }
    }

    // 2. Strict Header Validation: If claiming to be PNG, JPG, or PDF, verify real header!
    if (this.validHeaders[ext]) {
      const allowedPatterns = this.validHeaders[ext];
      let headerValid = false;
      for (const pattern of allowedPatterns) {
        if (uint8.length >= pattern.length) {
          let pMatch = true;
          for (let i = 0; i < pattern.length; i++) {
            if (uint8[i] !== pattern[i]) {
              pMatch = false;
              break;
            }
          }
          if (pMatch) {
            headerValid = true;
            break;
          }
        }
      }
      if (!headerValid) {
        return `Fake ${ext} detected! The binary header does not match a valid ${ext} file.`;
      }
    }

    return null;
  }
};

if (typeof module !== 'undefined') {
  module.exports = DLP_RULES;
}
