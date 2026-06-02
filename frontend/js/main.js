// frontend/js/main.js

const API_BASE = ""; // same origin (Flask)

// ---------------- GLOBAL STATE ----------------
let ALL_PLANTS = [];
let LAST_PREDICTED_PLANT = null;

// ---------------- DOM ELEMENTS ----------------
const plantCardsEl = document.getElementById("plantCards");
const diseaseInput = document.getElementById("diseaseQuery");
const doSearchBtn = document.getElementById("doSearch");

const navPredict = document.getElementById("navPredict");
const navBrowse = document.getElementById("navBrowse");
const navAdd = document.getElementById("navAdd");

// Modal elements
const detailsModal = document.getElementById("detailsModal");
const closeDetails = document.getElementById("closeDetails");
const detailName = document.getElementById("detailName");
const detailSci = document.getElementById("detailSci");
const detailParts = document.getElementById("detailParts");
const detailUses = document.getElementById("detailUses");
const detailRegion = document.getElementById("detailRegion");

// Prediction details
const viewDetailsBtn = document.getElementById("viewDetailsBtn");

// Cards header
const cardsTitleEl = document.getElementById("cardsTitle");
const cardsSubtitleEl = document.getElementById("cardsSubtitle");

// ---------------- HELPERS ----------------
function setCardsHeader(title, subtitle = "") {
  if (cardsTitleEl) cardsTitleEl.textContent = title;
  if (cardsSubtitleEl) cardsSubtitleEl.textContent = subtitle;
}

// ---------------- FETCH ALL PLANTS ----------------
async function fetchPlants() {
  try {
    const res = await fetch(`/plants`);
    const data = await res.json();
    ALL_PLANTS = data.plants || [];

    setCardsHeader(
      "All medicinal plants",
      "Browse all plants known in the RemedyRoot database."
    );

    renderPlantCards(ALL_PLANTS);
  } catch (err) {
    console.error("Error fetching plants:", err);
  }
}

// ---------------- RENDER CARDS ----------------
function renderPlantCards(plants) {
  plantCardsEl.innerHTML = "";

  if (!plants.length) {
    plantCardsEl.innerHTML = `
      <div class="text-sm text-gray-500 border border-dashed border-gray-300 rounded-lg p-3 text-center">
        No plants found for this filter.
      </div>`;
    return;
  }

  const grid = document.createElement("div");
  grid.className = "grid gap-3 sm:grid-cols-1 md:grid-cols-1";

  plants.forEach((p) => {
    const card = document.createElement("div");
    card.className =
      "border border-green-100 rounded-lg p-3 cursor-pointer bg-gradient-to-br from-green-50 to-emerald-50 hover:from-green-100 hover:to-emerald-100 hover:shadow-md transition transform hover:-translate-y-0.5";

    const usesPreview = (p.uses || "").slice(0, 90);
    const hasMore = (p.uses || "").length > 90;

    card.innerHTML = `
      <div class="flex items-start justify-between gap-2">
        <div>
          <h5 class="font-semibold text-green-800 text-sm md:text-base">${p.name || "Unknown"}</h5>
          <p class="text-[11px] md:text-xs text-gray-600 italic">${p.scientific_name || ""}</p>
        </div>
      </div>
      <p class="text-[11px] md:text-xs text-gray-700 mt-2">
        <span class="font-semibold">Uses:</span>
        ${usesPreview}${hasMore ? "…" : ""}
      </p>
      <p class="text-[11px] md:text-xs text-gray-700 mt-1">
        <span class="font-semibold">Region:</span> ${p.region || "N/A"}
      </p>
    `;

    card.addEventListener("click", () => openDetails(p));
    grid.appendChild(card);
  });

  plantCardsEl.appendChild(grid);
}

// ---------------- SEARCH BY DISEASE ----------------
doSearchBtn.addEventListener("click", async () => {
  const query = diseaseInput.value.trim();
  if (!query) {
    setCardsHeader(
      "All medicinal plants",
      "Browse all plants known in the RemedyRoot database."
    );
    renderPlantCards(ALL_PLANTS);
    return;
  }

  try {
    const res = await fetch(`/search_disease?q=${encodeURIComponent(query)}`);
    const data = await res.json();

    if (data.success) {
      setCardsHeader(
        `Results for "${query}"`,
        data.source === "firebase"
          ? "Showing plants from database."
          : "Showing internet-based results."
      );

      renderPlantCards(data.plants || []);
    } else {
      setCardsHeader(`No results for "${query}"`, "Try another symptom.");
      renderPlantCards([]);
    }
  } catch (err) {
    console.error("Search error:", err);
    setCardsHeader("Search error", "Unable to contact backend.");
    renderPlantCards([]);
  }
});

// ---------------- DETAILS MODAL ----------------
function openDetails(p) {
  detailName.textContent = p.name || "Unknown";
  detailSci.textContent = p.scientific_name || "N/A";
  detailParts.textContent = p.parts || "N/A";
  detailUses.textContent = p.uses || "N/A";
  detailRegion.textContent = p.region || "N/A";

  detailsModal.classList.remove("hidden");
  detailsModal.classList.add("flex");
}

function closeDetailsModal() {
  detailsModal.classList.add("hidden");
  detailsModal.classList.remove("flex");
}

closeDetails.addEventListener("click", closeDetailsModal);

detailsModal.addEventListener("click", (e) => {
  if (e.target === detailsModal) closeDetailsModal();
});

if (viewDetailsBtn) {
  viewDetailsBtn.addEventListener("click", () => {
    if (LAST_PREDICTED_PLANT) openDetails(LAST_PREDICTED_PLANT);
  });
}

// ---------------- NAVIGATION (with FIXED TEXT COLOR) ----------------
function setActiveNav(view) {
  [navPredict, navBrowse, navAdd].forEach((btn) => {
    btn.classList.remove("active", "bg-green-700", "text-white");
    btn.style.color = ""; // reset so CSS can apply
  });

  let activeBtn = null;
  if (view === "predict") activeBtn = navPredict;
  if (view === "browse") activeBtn = navBrowse;
  if (view === "add") activeBtn = navAdd;

  if (activeBtn) {
    activeBtn.classList.add("active", "bg-green-700", "text-white");
    activeBtn.style.color = "white"; // force visible text
  }
}

navPredict.addEventListener("click", () => setActiveNav("predict"));

navBrowse.addEventListener("click", () => {
  setActiveNav("browse");
  plantCardsEl.scrollIntoView({ behavior: "smooth" });
});

navAdd.addEventListener("click", () => {
  setActiveNav("add");
  if (window.showAddPlantModal) window.showAddPlantModal();
});

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", () => fetchPlants());

window.REMEDYROOT_STATE = {
  ALL_PLANTS,
  setPredictedPlant: (p) => (LAST_PREDICTED_PLANT = p),
  refreshPlants: fetchPlants,
};
