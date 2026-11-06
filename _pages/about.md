---
permalink: /
title: ""
excerpt: ""
author_profile: true
redirect_from: 
  - /about/
  - /about.html
---

<span class='anchor' id='about-me'></span>

I am a 4th-year Ph.D. student from the School of [Computer Science](https://cs.fudan.edu.cn/), [Fudan University](https://www.fudan.edu.cn/).
My research interests include   
- *natural language processing*, 
- *efficient machine learning and downstream adaptation* and 
- *scaling of reinforcement learning*.

I am fortunate to be advised by [Prof. Yu Wang](https://yuwangsjtu.github.io/) and [Prof. Ya Zhang](https://mediabrain.sjtu.edu.cn/yazhang/). My [CV](/pdf/resume.pdf) is available here.


# 🎓 Educations
- *2023.06 - Current*, <a href="https://www.fdu.edu.cn/"><img class="png" src="/images/fdu_logo.png" width="20" height="20" loading="lazy" alt="Fudan University logo"></a> Fudan University, School of Computer Science, Shanghai, Ph.D.
- *2019.09 - 2023.06*, <a href="https://www.sjtu.edu.cn/"><img class="png" src="/images/sjtu_logo.png" width="23" height="23" loading="lazy" alt="Shanghai Jiao Tong University logo"></a> Shanghai Jiao Tong University, School of Electronic Information and Electrical Engineering, Shanghai, Bachelor Degree
 
# 📝 Publications

### Highlight
---
{% for paper in site.data.publications.highlight %}
{% include paper-card.html paper=paper %}
{% endfor %}

### Others
---
{% for paper in site.data.publications.others %}
{% include paper-card.html paper=paper %}
{% endfor %}

# 💻 Internships
- *2022.01 - 2023.04*, Shanghai Artificial Intelligence Laboratory, Intern Researcher
- *2026.07 - present*, Tencent Workbuddy Team, Intern Researcher
