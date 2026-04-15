const modal = document.getElementById("pixel-editor-modal");
const canvas = document.getElementById("pixel-canvas");
const ctx = canvas ? canvas.getContext("2d") : null;
const colorInput = document.getElementById("pixel-color");
const size = 8;
const scale = 32;
let targetMode = "avatar";
let pixels = Array.from({ length: size }, () => Array(size).fill("#00000000"));

function drawGrid() {
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      ctx.fillStyle = pixels[y][x] === "#00000000" ? "#ffffff" : pixels[y][x];
      ctx.fillRect(x * scale, y * scale, scale, scale);
      ctx.strokeStyle = "#999";
      ctx.strokeRect(x * scale, y * scale, scale, scale);
    }
  }
}

function resetPixels() {
  pixels = Array.from({ length: size }, () => Array(size).fill("#00000000"));
  drawGrid();
}
drawGrid();

let painting = false;
function paintAtEvent(e) {
  if (!colorInput || !canvas) return;
  const rect = canvas.getBoundingClientRect();
  const x = Math.floor((e.clientX - rect.left) / scale);
  const y = Math.floor((e.clientY - rect.top) / scale);
  if (x < 0 || x >= size || y < 0 || y >= size) return;
  pixels[y][x] = colorInput.value;
  drawGrid();
}
canvas?.addEventListener("mousedown", (e) => {
  painting = true;
  paintAtEvent(e);
});
window.addEventListener("mouseup", () => (painting = false));
canvas?.addEventListener("mousemove", (e) => {
  if (!painting || !colorInput) return;
  paintAtEvent(e);
});

window.openPixelEditor = ({ target }) => {
  targetMode = target || "avatar";
  modal?.classList.remove("hidden");
};
document.getElementById("pixel-close")?.addEventListener("click", () => modal?.classList.add("hidden"));
document.getElementById("pixel-clear")?.addEventListener("click", resetPixels);

document.getElementById("pixel-save")?.addEventListener("click", () => {
  const out = document.createElement("canvas");
  out.width = size;
  out.height = size;
  const outCtx = out.getContext("2d");
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const c = pixels[y][x];
      if (c !== "#00000000") {
        outCtx.fillStyle = c;
        outCtx.fillRect(x, y, 1, 1);
      }
    }
  }
  out.toBlob((blob) => {
    if (!blob) return;
    const file = new File([blob], "pixel8x8.png", { type: "image/png" });
    if (targetMode === "compose" && window.addComposeGalleryItem) {
      window.addComposeGalleryItem(file);
    } else {
      const formData = new FormData();
      formData.append("avatar", file, "pixel8x8.png");
      fetch("/profile/avatar", { method: "POST", body: formData, credentials: "same-origin" })
        .then((res) => {
          if (res.ok) {
            window.location.reload();
          } else {
            alert(`Не удалось сохранить аватар (${res.status}). Проверьте, что PNG ровно 8x8.`);
          }
        })
        .catch(() => alert("Не удалось сохранить аватар."));
    }
    modal?.classList.add("hidden");
  }, "image/png");
});

document.getElementById("open-avatar-editor")?.addEventListener("click", () => window.openPixelEditor({ target: "avatar" }));
