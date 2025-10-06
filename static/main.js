const formWord = document.getElementById('form-word');
const formFilter = document.getElementById('form-filter');
const setWord = document.getElementById('set-word');
const setFilter = document.getElementById('set-filter');
const btnSearch = document.getElementById('btn-search');

setWord.addEventListener('click', () => {
    btnSearch.setAttribute('form', 'form-word');
    setWord.style.opacity = '1.0';
    setFilter.style.opacity = '0.2';
    formFilter.style.display = "none";
    formWord.style.display = "";
});

setFilter.addEventListener('click', () => {
    btnSearch.setAttribute('form', 'form-filter');
    setFilter.style.opacity = '1.0';
    setWord.style.opacity = '0.2';
    formWord.style.display = "none";
    formFilter.style.display = "";
});

let page = 0;
let videosAll;
let loading = true;
const VIDEO_PER_PAGE = 20;

const containerVideo = document.getElementById("videos");

document.addEventListener('DOMContentLoaded', () => {
    fetch('/search-filter')
        .then(res => res.json())
        .then(videos => {
            videosAll = videos;
            appendVideos(videosAll.slice(0, VIDEO_PER_PAGE));
            page = 1;
            loading = false;
        })
})

formFilter.addEventListener("submit", (e) => {
    e.preventDefault(); // buttonによってGETリクエストが飛ぶのを止める

    loading = true; // innerHTML = '' したときにobserverが反応するのを防ぐ
    containerVideo.innerHTML = '';

    const form = e.target;
    const params = new URLSearchParams(new FormData(form));
    fetch(form.action + "?" + params.toString())
        .then(res => res.json())
        .then(videos => {
            videosAll = videos;
            appendVideos(videosAll.slice(0, VIDEO_PER_PAGE));
            page = 1;
            loading = false;
        })
});

formWord.addEventListener("submit", (e) => {
    e.preventDefault();

    loading = true;
    containerVideo.innerHTML = '';

    const form = e.target;
    const params = new URLSearchParams(new FormData(form));
    fetch(form.action + "?" + params.toString())
        .then(res => res.json())
        .then(videos => {
            videosAll = videos;
            appendVideos(videosAll.slice(0, VIDEO_PER_PAGE));
            page = 1;
            loading = false;
        })
});

const observer = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting && !loading) {
        appendVideos(videosAll.slice(page * VIDEO_PER_PAGE, (page + 1) * VIDEO_PER_PAGE));
        page += 1;
    }
});
const sentinel = document.getElementById("sentinel");
observer.observe(sentinel);

function appendVideos(videos) {
    videos.forEach(row => {
        const div = document.createElement("div");
        div.className = "video";
        div.innerHTML = `
      <div class="container-thumbnail">
        <a href="https://www.youtube.com/watch?v=${row.id_video}">
          <img src="${row.thumbnail_url}" alt="thumbnail" class="thumbnail">
        </a>
      </div>
      <div>
        <a href="https://www.youtube.com/watch?v=${row.id_video}">
          <div class="title">${row.title}</div>
        </a>
        <div style="display: flex">
          <a href="https://www.youtube.com/channel/${row.id_channel}">
            <div class="channel">${row.channel}</div>
          </a>
          <div class="category" style="background-color:${row.color}">${row.category}</div>
          <div class="time">${row.time_watch}</div>
        </div>
      </div>
    `;
        containerVideo.appendChild(div);
    });
}
