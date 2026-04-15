const html = document.documentElement;

function syncThemeToggleLabels() {
  const dark = html.classList.contains("dark-mode");
  const label = dark ? "Тема: тёмная" : "Тема: светлая";
  document.querySelectorAll(".theme-toggle").forEach((btn) => {
    btn.setAttribute("aria-checked", dark ? "true" : "false");
    btn.textContent = label;
  });
}

function toggleTheme() {
  html.classList.toggle("dark-mode");
  const dark = html.classList.contains("dark-mode");
  localStorage.setItem("minisocial-theme", dark ? "dark" : "light");
  syncThemeToggleLabels();
}

document.querySelectorAll(".theme-toggle").forEach((btn) => {
  btn.addEventListener("click", toggleTheme);
});
syncThemeToggleLabels();

const composeModal = document.getElementById("compose-modal");
const openCompose = document.getElementById("open-compose");
const closeCompose = document.getElementById("close-compose");
const closeComposeX = document.getElementById("close-compose-x");
if (openCompose && composeModal) {
  openCompose.onclick = () => {
    composeModal.classList.remove("hidden");
    postContent?.focus();
  };
}
if (closeCompose && composeModal) closeCompose.onclick = () => composeModal.classList.add("hidden");
if (closeComposeX && composeModal) closeComposeX.onclick = () => composeModal.classList.add("hidden");

const postContent = document.getElementById("post-content");
const charCount = document.getElementById("char-count");
if (postContent && charCount) {
  const updateCount = () => { charCount.textContent = String(postContent.value.length); };
  const autoHeight = () => {
    postContent.style.height = "auto";
    postContent.style.height = `${postContent.scrollHeight}px`;
  };
  postContent.addEventListener("input", updateCount);
  postContent.addEventListener("input", autoHeight);
  updateCount();
  autoHeight();
}

const galleryList = document.getElementById("gallery-list");
let composeItems = [];
function rerenderGallery() {
  if (!galleryList) return;
  galleryList.innerHTML = "";
  composeItems.forEach((item, idx) => {
    const div = document.createElement("div");
    div.className = "row";
    const kindLabel = item.kind === "file" ? "файл" : "ссылка";
    div.innerHTML = `<strong>${kindLabel}</strong> ${item.name || item.url || "(рисунок)"} <button type="button">Удалить</button>`;
    div.querySelector("button").onclick = () => {
      composeItems = composeItems.filter((_, i) => i !== idx);
      rerenderGallery();
    };
    galleryList.appendChild(div);
  });
}
window.addComposeGalleryItem = (file) => {
  composeItems.push({ kind: "file", name: file.name, file });
  rerenderGallery();
};

const addFileBtn = document.getElementById("add-gallery-file");
if (addFileBtn) {
  addFileBtn.onclick = () => {
    const i = document.createElement("input");
    i.type = "file";
    i.accept = "image/*";
    i.onchange = () => {
      if (i.files && i.files[0]) window.addComposeGalleryItem(i.files[0]);
    };
    i.click();
  };
}

const addUrlBtn = document.getElementById("add-gallery-url");
if (addUrlBtn) {
  addUrlBtn.onclick = () => {
    const url = prompt("Ссылка на изображение (http/https)");
    if (!url) return;
    composeItems.push({ kind: "url", url });
    rerenderGallery();
  };
}
const addDrawBtn = document.getElementById("add-gallery-draw");
if (addDrawBtn) addDrawBtn.onclick = () => window.openPixelEditor && window.openPixelEditor({ target: "compose" });

const emojiButton = document.getElementById("open-emoji");
const emojiPopover = document.getElementById("emoji-popover");
let emojiPicker;
const fallbackEmoji = ["😀", "😂", "😍", "😎", "🤔", "😭", "🔥", "❤️", "👍", "🙏", "🎉", "✅"];
const closeEmojiPopover = () => {
  emojiPopover?.classList.add("hidden");
  if (emojiPicker) emojiPicker.remove();
  emojiPicker = null;
};
window.closeEmojiWcPopover = closeEmojiPopover;
if (emojiButton && emojiPopover && postContent) {
  emojiButton.addEventListener("click", () => {
    if (emojiPicker) {
      closeEmojiPopover();
      return;
    }
    emojiPopover.classList.remove("hidden");
    const insertEmoji = (emoji) => {
      const start = postContent.selectionStart ?? postContent.value.length;
      const end = postContent.selectionEnd ?? postContent.value.length;
      const nextValue = `${postContent.value.slice(0, start)}${emoji}${postContent.value.slice(end)}`;
      if (nextValue.length > Number(postContent.maxLength || 100000)) return;
      postContent.value = nextValue;
      const pos = start + emoji.length;
      postContent.setSelectionRange(pos, pos);
      postContent.dispatchEvent(new Event("input", { bubbles: true }));
      postContent.focus();
    };
    const supportsEmojiWc = typeof customElements !== "undefined" && customElements.get("emoji-picker");
    if (supportsEmojiWc) {
      emojiPicker = document.createElement("emoji-picker");
      emojiPicker.setAttribute("theme", html.classList.contains("dark-mode") ? "dark" : "light");
      emojiPicker.addEventListener("emoji-click", (event) => {
        insertEmoji(event?.detail?.unicode || "");
      });
      emojiPopover.appendChild(emojiPicker);
    } else {
      emojiPicker = document.createElement("div");
      emojiPicker.className = "emoji-list";
      fallbackEmoji.forEach((emoji) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = emoji;
        btn.addEventListener("click", () => insertEmoji(emoji));
        emojiPicker.appendChild(btn);
      });
      emojiPopover.appendChild(emojiPicker);
    }
  });
}

const composeForm = document.getElementById("compose-form");
if (composeForm) {
  composeForm.addEventListener("submit", () => {
    composeForm.querySelectorAll(".dyn-field").forEach((n) => n.remove());
    const count = Math.min(4, composeItems.length);
    const appendHidden = (name, value) => {
      const i = document.createElement("input");
      i.type = "hidden";
      i.name = name;
      i.value = value;
      i.className = "dyn-field";
      composeForm.appendChild(i);
    };
    appendHidden("gallery_count", String(count));
    composeItems.slice(0, count).forEach((item, idx) => {
      appendHidden(`gallery_kind_${idx}`, item.kind);
      if (item.kind === "url") {
        appendHidden(`gallery_url_${idx}`, item.url);
      } else {
        const f = document.createElement("input");
        f.type = "file";
        f.name = `gallery_file_${idx}`;
        f.className = "dyn-field";
        const dt = new DataTransfer();
        dt.items.add(item.file);
        f.files = dt.files;
        f.style.display = "none";
        composeForm.appendChild(f);
      }
    });
  });
}

composeModal?.addEventListener("click", (e) => {
  if (e.target === composeModal) {
    composeModal.classList.add("hidden");
    closeEmojiPopover();
  }
});

document.querySelectorAll("form[data-confirm]").forEach((f) => {
  f.addEventListener("submit", (e) => {
    if (!confirm(f.dataset.confirm || "Вы уверены?")) e.preventDefault();
  });
});

document.querySelectorAll(".like-form").forEach((form) => {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const postId = form.dataset.postId;
    if (!postId) return;
    const res = await fetch(`/api/posts/${postId}/like`, { method: "POST" });
    if (!res.ok) return form.submit();
    const payload = await res.json();
    if (!payload.ok) return;
    form.querySelector(".like-count").textContent = String(payload.likes);
    form.querySelector(".like-btn").textContent = payload.liked ? "Убрать лайк" : "Лайк";
  });
});

const lightbox = document.getElementById("lightbox");
const lightboxImage = document.getElementById("lightbox-image");
const lightboxItems = [...document.querySelectorAll(".lightbox-item")];
let lightboxIndex = 0;
const showLightbox = (idx) => {
  if (!lightbox || !lightboxImage || !lightboxItems[idx]) return;
  lightboxIndex = idx;
  lightboxImage.src = lightboxItems[idx].src;
  lightbox.classList.remove("hidden");
};
lightboxItems.forEach((img, idx) => img.addEventListener("click", () => showLightbox(idx)));
document.getElementById("lightbox-prev")?.addEventListener("click", () => showLightbox((lightboxIndex - 1 + lightboxItems.length) % lightboxItems.length));
document.getElementById("lightbox-next")?.addEventListener("click", () => showLightbox((lightboxIndex + 1) % lightboxItems.length));
lightbox?.addEventListener("click", (e) => { if (e.target === lightbox) lightbox.classList.add("hidden"); });
window.addEventListener("keydown", (e) => {
  if (!lightbox || lightbox.classList.contains("hidden")) return;
  if (e.key === "Escape") lightbox.classList.add("hidden");
});
