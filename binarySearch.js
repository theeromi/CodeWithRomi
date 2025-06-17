const array = [2, 5, 8, 12, 16, 23, 38, 45, 56, 72];
const container = document.getElementById("array-container");

function renderArray() {
  container.innerHTML = "";
  array.forEach((num, idx) => {
    const box = document.createElement("div");
    box.className = "box";
    box.textContent = num;
    box.id = "box-" + idx;
    container.appendChild(box);
  });
}

function highlight(index, className) {
  const box = document.getElementById("box-" + index);
  if (box) {
    box.className = "box " + className;
  }
}

async function startSearch() {
  renderArray();
  const target = parseInt(document.getElementById("search-value").value);
  if (isNaN(target)) return alert("Enter a number!");

  let left = 0;
  let right = array.length - 1;

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);

    highlight(mid, "searching");
    await new Promise(res => setTimeout(res, 800));

    if (array[mid] === target) {
      highlight(mid, "found");
      return;
    } else {
      highlight(mid, "skipped");
      if (array[mid] < target) {
        left = mid + 1;
      } else {
        right = mid - 1;
      }
    }
  }

  alert("Value not found.");
}
renderArray();
