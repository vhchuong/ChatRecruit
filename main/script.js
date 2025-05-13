// Store analysis results globally so we can access them when downloading
let currentResults = null;

document.getElementById("uploadForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const formData = new FormData();
  formData.append("jd", document.getElementById("jd").files[0]);
  const cvs = document.getElementById("cvs").files;
  for (let i = 0; i < cvs.length; i++) {
      formData.append("cvs", cvs[i]);
  }

  // Show spinner
  document.getElementById("spinner").classList.remove("hidden");
  document.getElementById("status").innerText = "Uploading and analyzing...";
  document.getElementById("results").innerHTML = "";
  
  // Hide download button when starting a new analysis
  const downloadBtn = document.getElementById("downloadExcelBtn");
  downloadBtn.classList.add("hidden");
  downloadBtn.disabled = true;
  
  // Reset stored results
  currentResults = null;

  try {
      const response = await fetch("/upload", {
          method: "POST",
          body: formData
      });

      const data = await response.json();

      document.getElementById("status").innerText = "Analysis complete";
      const results = data.results;
      
      // Store results for later use with the download button
      currentResults = results;

      let html = `<div class="overflow-x-auto">
          <table class="table-auto w-full border-collapse bg-white rounded-lg shadow-md">
              <thead>
                  <tr class="bg-indigo-600 text-white">
                      <th class="px-4 py-2 text-left">Rank</th>
                      <th class="px-4 py-2 text-left">File</th>
                      <th class="px-4 py-2 text-left">Score</th>
                      <th class="px-4 py-2 text-left">Match Level</th>
                      <th class="px-4 py-2 text-left">Strength</th>
                      <th class="px-4 py-2 text-left">Weakness</th>
                  </tr>
              </thead>
              <tbody>`;

      results.forEach((r, i) => {
          html += `
              <tr class="border-t">
                  <td class="px-4 py-2">${i + 1}</td>
                  <td class="px-4 py-2">${r.filename}</td>
                  <td class="px-4 py-2">${r.score}</td>
                  <td class="px-4 py-2">${r.match_level}</td>
                  <td class="px-4 py-2">
                  <ul class="list-disc pl-5 space-y-1 text-gray-700">
                      ${r.strength.map(item => `<li>${item}</li>`).join("")}
                  </ul>
                  </td>
                  <td class="px-4 py-2">
                      <ul class="list-disc pl-5 space-y-1 text-gray-700">
                          ${r.weakness.map(item => `<li>${item}</li>`).join("")}
                      </ul>
                  </td>
                  </tr>`;
      });

      html += `</tbody></table></div>`;
      document.getElementById("results").innerHTML = html;
      
      // Show and enable download button
      downloadBtn.disabled = false;
      downloadBtn.classList.remove("hidden");

  } catch (err) {
      console.error("Error during analysis:", err);
      document.getElementById("status").innerText = "Error during analysis.";
  }

  // Hide spinner
  document.getElementById("spinner").classList.add("hidden");
});

// Add event listener for the download button
document.getElementById("downloadExcelBtn").addEventListener("click", async function() {
  if (!currentResults) {
    document.getElementById("status").innerText = "No results to download";
    return;
  }
  
  try {
    document.getElementById("status").innerText = "Generating Excel file...";
    
    const response = await fetch("/download-excel", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(currentResults)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`);
    }
    
    // Create a blob from the response
    const blob = await response.blob();
    
    // Create a link to download the file
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = "cv_analysis_report.xlsx";
    
    // Add to the DOM and trigger download
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    document.getElementById("status").innerText = "Excel file downloaded successfully";
    
  } catch (err) {
    console.error("Error downloading Excel:", err);
    document.getElementById("status").innerText = "Error generating Excel file";
  }
});
