let selectedPhotoIds = [];

const photoGrid = document.getElementById("photo-grid");
const deleteBtn = document.getElementById("delete-btn");
const countSpan = document.getElementById("count");

countSpan.hidden = true;

photoGrid.addEventListener("click", function (event) {
  const photoItem = event.target.closest(".photo-item");

  if (!photoItem) return;

  const rawId = photoItem.dataset.photoId;
  const photoId = Number(rawId);

  if (!Number.isInteger(photoId)) {
    console.warn(`skipping invalid photoId:  ${rawId}`);
    return;
  }

  if (selectedPhotoIds.includes(photoId)) {
    selectedPhotoIds = selectedPhotoIds.filter((id) => id !== photoId);
    photoItem.classList.remove("opacity-50");
  } else {
    selectedPhotoIds.push(photoId);
    photoItem.classList.add("opacity-50");
  }
  updateDeleteButton();
});

function updateDeleteButton() {
  const count = selectedPhotoIds.length;

  countSpan.textContent = count;
  deleteBtn.disabled = count === 0;

  countSpan.hidden = count === 0;
}

deleteBtn.addEventListener("click", async function () {
  if (selectedPhotoIds.length === 0) return;

  if (!confirm(`Delete ${selectedPhotoIds.length} photos?`)) return;

  deleteBtn.disabled = true;
  deleteBtn.textContent = "Deleting...";

  try {
    const response = await fetch("/admin/photos/delete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ photo_ids: selectedPhotoIds }),
    });

    if (response.ok) {
      window.location.reload();
    } else {
      alert("Error deleting photos");
      deleteBtn.disabled = false;
      // deleteBtn.textContent = `Delete selected (${selectedPhotoIds.length})`;
    }
  } catch (error) {
    alert("Network Error: " + error.message);
    deleteBtn.disabled = false;
    // deleteBtn.textContent = `Delete selected (${selectedPhotoIds.length})`;
  }
});
