(() => {
  "use strict";
  const isAv1 = type => typeof type === "string" && /\bav01\b/i.test(type);
  for (const source of [globalThis.MediaSource, globalThis.ManagedMediaSource]) {
    if (!source?.isTypeSupported) continue;
    const original = source.isTypeSupported;
    source.isTypeSupported = function (type) {
      return isAv1(type) ? false : Reflect.apply(original, this, [type]);
    };
  }
  const originalPlay = HTMLMediaElement.prototype.canPlayType;
  HTMLMediaElement.prototype.canPlayType = function (type) {
    return isAv1(type) ? "" : Reflect.apply(originalPlay, this, [type]);
  };
  if (navigator.mediaCapabilities?.decodingInfo) {
    const originalDecode = navigator.mediaCapabilities.decodingInfo.bind(navigator.mediaCapabilities);
    navigator.mediaCapabilities.decodingInfo = config => isAv1(config?.video?.contentType)
      ? Promise.resolve({ supported: false, smooth: false, powerEfficient: false })
      : originalDecode(config);
  }
})();
