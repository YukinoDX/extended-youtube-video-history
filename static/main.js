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
