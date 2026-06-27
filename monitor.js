  const handleIncomingWebcam = (data) => {
  const incomingMachine = data.machine_name;
  const activeSelection = getTargetMachine();

  if (incomingMachine !== activeSelection) return;
  if (!sessionStorage.getItem(`webcam_active_${incomingMachine}`)) return;

  const displayBox = getElementById('webcam-display-box');
  if (!displayBox) return;

  let imgElement = displayBox.querySelector('#live-webcam-img');
  if (!imgElement) {
    displayBox.innerHTML = `<img id="live-webcam-img" style="width:100%; height:auto; display:block; object-fit:contain; max-height:60vh;" alt="Webcam Feed" />`;
    imgElement = displayBox.querySelector('#live-webcam-img');
  }

  if (imgElement && data.image_base64) {
    let base64Str = data.image_base64;
    // Xử lý trường hợp base64 bị rác (wrapper bytes nếu có)
    if (base64Str.startsWith("b'") || base64Str.startsWith('b"')) {
      base64Str = base64Str.substring(2, base64Str.length - 1);
    }
    // Chuẩn hoá base64: loại newline
    const cleanBase64 = base64Str.replace(/(\r\n|\n|\r)/gm, "").trim();
    const mimeType = cleanBase64.charAt(0) === '/' ? 'jpeg' : 'png';
    imgElement.src = `data:image/${mimeType};base64,${cleanBase64}`;
  }
};