// frontend/js/predict.js
// expects backend to return { success, class_id, confidence, plant }
console.log("predict.js loaded");

const API_URL = "http://127.0.0.1:5000";

const fileInput = document.getElementById("predictImage");
const doPredictBtn = document.getElementById("doPredict");
const predictPreview = document.getElementById("predictPreview");
const predictionCard = document.getElementById("predictionCard");
const predictPlaceholder = document.getElementById("predictPlaceholder");
const predictLoading = document.getElementById("predictLoading");
const predictedName = document.getElementById("predictedName");
const predictedParts = document.getElementById("predictedParts");
const predictedUses = document.getElementById("predictedUses");
const ViewDetailsBtn = document.getElementById("ViewDetailsBtn");


let lastPrediction = null;

fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
        predictPreview.src = e.target.result;
        predictPreview.classList.remove("hidden");
    };
    reader.readAsDataURL(file);
});

doPredictBtn.addEventListener("click", async () => {
    if (!fileInput.files.length) {
        alert("Please choose an image first!");
        return;
    }

    const fd = new FormData();
    fd.append("file", fileInput.files[0]);

    predictPlaceholder.classList.add("hidden");
    predictionCard.classList.add("hidden");
    predictLoading.classList.remove("hidden");

    try {
        const res = await fetch(`${API_URL}/predict`, {
            method: "POST",
            body: fd
        });

        if (!res.ok) {
            const err = await res.json().catch(()=>({error:"server error"}));
            alert("Server error: " + (err.error || JSON.stringify(err)));
            predictLoading.classList.add("hidden");
            return;
        }

        const data = await res.json();
        console.log("Backend returned:", data);
        predictLoading.classList.add("hidden");

        if (!data.success) {
            alert("Prediction error: " + (data.error || "unknown"));
            return;
        }

        const plant = data.plant || null;

        if (plant) {
    predictedName.innerText = plant.name || `Class ${data.class_id}`;
    lastPrediction = plant;
} else {
    predictedName.innerText = `Class ${data.class_id}`;
    lastPrediction = null;
}

/* clear details during predict */
predictedParts.innerText = "";
predictedUses.innerText = "";


        predictionCard.classList.remove("hidden");

    } catch (err) {
        console.error("Predict error:", err);
        predictLoading.classList.add("hidden");
        alert("Could not reach backend.");
    }
});

viewDetailsBtn.addEventListener("click", () => {
    if (!lastPrediction) return;
    document.getElementById("detailName").innerText = lastPrediction.name;
    document.getElementById("detailSci").innerText = lastPrediction.scientific || "";
    document.getElementById("detailParts").innerText = Array.isArray(lastPrediction.parts) ? lastPrediction.parts.join(", ") : (lastPrediction.parts || "");
    document.getElementById("detailUses").innerText = lastPrediction.uses || "";
    document.getElementById("detailRegion").innerText = lastPrediction.region || "";
    document.getElementById("detailsModal").classList.remove("hidden");
});
