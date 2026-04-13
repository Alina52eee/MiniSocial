import "https://cdn.jsdelivr.net/npm/emoji-picker-element@^1/index.js";

window.closeEmojiWcPopover = function closeEmojiWcPopover() {
  const picker = document.querySelector("emoji-picker");
  picker?.remove();
};
