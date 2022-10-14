// Get score percentage and make width of progress bar

window.onload = function() {

	pBar = document.getElementById('progressbar');
	score = document.getElementById('score-percent');

	var upsNum = +document.getElementById('p-ups').innerHTML;
	var downsNum = +document.getElementById('p-downs').innerHTML;

	var sum = upsNum + downsNum;

	var val = (Math.floor((upsNum / sum) * 100));

	// console log var val for troubleshooting

	console.log(val);

	score.innerHTML = val + "% upvoted";

	pBar.style.width = val + "%";

	// Set background color of progress bar based on score

	if (val < 50) {
		pBar.classList.remove("bg-upvote");
		pBar.classList.add("bg-downvote");
	}
}
