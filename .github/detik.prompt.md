



get kanal() from https://finance.detik.com/indeks

<div class="column-3">
			<nav class=" static-nav sticky">
    <ul class="nav nav--column">

                        <li class="nav__item ">
            <a href="https://news.detik.com/indeks" onclick="_pt(this, &quot;menu kanal&quot;, &quot;menu kanal&quot;, &quot;menu News&quot;)">
                <div>News</div>
                <i class="icon icon-chevron-right"></i>
            </a>
        </li>
                <li class="nav__item ">
            <a href="https://www.detik.com/edu/indeks" onclick="_pt(this, &quot;menu kanal&quot;, &quot;menu kanal&quot;, &quot;menu Edu&quot;)">
                <div>Edu</div>
                <i class="icon icon-chevron-right"></i>
            </a>
        
    </ul>
</nav>
		</div>



get sub_kanal() from a kanal

<div class="indeks-menu">
        <h2 class="indeks-menu__title">detikFinance</h2>
        <div class="indeks-menu__box">
            <span>Pilih Sub Kanal</span>
            <div>
                <select id="select_nav_indeks" class="form-element">
                    <option value="">Semua Berita</option>
                                        <option value="/berita-ekonomi-bisnis">Berita Ekonomi Bisnis</option>
                                        <option selected="" value="/finansial">Finansial</option>
                                        <option value="/properti">Properti</option>
                                        <option value="/energi">Energi</option>
                                        <option value="/industri">Industri</option>
                                    </select>
            </div>
        </div>
    </div>



get article list from

https://{kanal}/indeks?page={page}&date={date}
https://finance.detik.com/indeks?page=2&date=07/28/2025

incremental until empty
:

<a href="https://finance.detik.com/foto-bisnis/d-8032723/bulog-kirim-13-ton-beras-ke-pulau-terluar-aceh-lewat-jalur-laut" class="media__link" onclick="_pt(this, &quot;newsfeed&quot;, &quot;Bulog Kirim 13 Ton Beras ke Pulau Terluar Aceh Lewat Jalur Laut&quot;, &quot;artikel 2&quot;)">Bulog Kirim 13 Ton Beras ke Pulau Terluar Aceh Lewat Jalur Laut</a>