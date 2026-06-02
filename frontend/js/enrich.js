// frontend/js/enrich.js

const API_BASE_E = ""; // same origin

// Create Add Plant modal dynamically
const addPlantModal = document.createElement("div");
addPlantModal.id = "addPlantModal";
addPlantModal.className = "fixed inset-0 hidden items-center justify-center z-50";

addPlantModal.innerHTML = `
  <div class="backdrop absolute inset-0 bg-black/40"></div>
  <div class="relative bg-white rounded-lg shadow-lg w-11/12 md:w-2/3 p-6 z-10">
    <button id="closeAddPlant" class="absolute top-3 right-3 text-gray-500 text-xl">✕</button>

    <h3 class="text-xl font-bold text-green-800 mb-4">Add New Medicinal Plant</h3>

    <form id="addPlantForm" class="grid grid-cols-1 md:grid-cols-2 gap-4" enctype="multipart/form-data">

      <!-- Plant Name -->
      <div>
        <label class="block text-sm font-semibold mb-1">Plant Name</label>
        <input name="name" type="text" class="w-full border rounded px-2 py-1" required />
      </div>

      <!-- Region -->
      <div>
        <label class="block text-sm font-semibold mb-1">Region</label>
        <input name="region" type="text" class="w-full border rounded px-2 py-1" required />
      </div>

      <!-- Medicinal Parts -->
      <div class="md:col-span-2">
        <label class="block text-sm font-semibold mb-1">Medicinal Parts</label>
        <textarea name="parts" class="w-full border rounded px-2 py-1" rows="2" required></textarea>
      </div>

      <!-- Therapeutic Uses -->
      <div class="md:col-span-2">
        <label class="block text-sm font-semibold mb-1">Therapeutic Uses</label>
        <textarea name="uses" class="w-full border rounded px-2 py-1" rows="3" required></textarea>
      </div>

      <!-- Diseases -->
      <div class="md:col-span-2">
        <label class="block text-sm font-semibold mb-1">Diseases / Symptoms (comma separated)</label>
        <input name="diseases" type="text" class="w-full border rounded px-2 py-1" />
      </div>

      <!-- Upload Image -->
      <div class="md:col-span-2">
        <label class="block text-sm font-semibold mb-1">Upload Image</label>
        <input name="image_file" type="file" class="w-full border rounded px-2 py-1" accept="image/*" />
      </div>

      <!-- Actions -->
      <div class="md:col-span-2 flex justify-end mt-2 gap-2">
        <button type="button" id="cancelAddPlant" class="px-4 py-2 border rounded text-gray-700">
          Cancel
        </button>
        <button type="submit" class="px-4 py-2 bg-green-700 text-white rounded hover:bg-green-800">
          Save Plant
        </button>
      </div>

    </form>
  </div>
`;

document.body.appendChild(addPlantModal);

const closeAddBtn = document.getElementById("closeAddPlant");
const cancelAddBtn = document.getElementById("cancelAddPlant");
const addPlantForm = document.getElementById("addPlantForm");

// ---------- Modal open/close ----------
function showAddPlantModal() {
  addPlantModal.classList.remove("hidden");
  addPlantModal.classList.add("flex");
}

function hideAddPlantModal() {
  addPlantModal.classList.add("hidden");
  addPlantModal.classList.remove("flex");
}

closeAddBtn.addEventListener("click", hideAddPlantModal);
cancelAddBtn.addEventListener("click", hideAddPlantModal);
addPlantModal.addEventListener("click", (e) => {
  if (e.target === addPlantModal) hideAddPlantModal();
});

// ---------- Form Submit ----------
addPlantForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData(addPlantForm);

  try {
    const res = await fetch(`${API_BASE_E}/plants`, {
      method: "POST",
      body: formData
    });

    const data = await res.json();

    if (!data.success) {
      alert(data.error || "Failed to add plant.");
      return;
    }

    alert("Plant added successfully!");

    // Refresh plant list
    if (window.REMEDYROOT_STATE && window.REMEDYROOT_STATE.refreshPlants) {
      window.REMEDYROOT_STATE.refreshPlants();
    }

    addPlantForm.reset();
    hideAddPlantModal();

  } catch (err) {
    console.error(err);
    alert("Error while adding plant.");
  }
});

// Expose modal open fn globally
window.showAddPlantModal = showAddPlantModal;
