# Trade credit financing, social trust, and financial distress_ Evidence from Chinese listed companies 逆向工程分析

### 0) 文献身份锚点
- **文献编号**：[8]
- **锁定引用**：Tang et al. (2025)
- **核心标签**：商业信用融资、财务困境、社会信任

### 1) 核心假设（Premise）
**分析：** 在文献 [8] 中，Tang 等人 (2025) 的研究从商业信用对财务困境的影响存在争议这一学术分歧出发。其核心假设是，过去研究结论的不一致（即商业信用可能降低或增加风险）是因为忽视了二者之间可能存在的非线性关系。隐藏的假设是，商业信用的“流动性缓冲”效应和“风险传染”效应会共同发挥作用，且强度随商业信用使用水平的变化而变化，从而形成U型关系。此外，研究还假设社会信任作为一种非正式制度，能够调节这种U型关系。
**原文铁证：**

> > “However, these studies have not reached a consensus in their findings; consequently, trade credit’s relationship with bankruptcy remains in dispute.” (Section 1, p.1)
> “We argue that both positions have solid support and that they act jointly. While the liquidity buffer effect is monotonically decreasing with diminishing margins, firms’ risk of contagion simultaneously rises monotonically. Taken together, the two opposing forces may lead to a U-shaped relationship between trade credit financing and bankruptcy risk.” (Section 2.1, p.3)
> “Thus, we expect the non-monotonic U-shaped impact of trade credit on firm bankruptcy risk to be less pronounced for firms in regions with high social trust.” (Section 2.2, p.4)

### 2) 推演路径（Inference）
**分析：** 在文献 [8] 中，推演路径从理论争议出发，逐步构建假设并验证，形成A→B→C的链条。
- **A. 理论起点与矛盾识别：** 识别出关于商业信用作用的两种对立观点（流动性缓冲 vs. 风险传染），并指出这是导致现有研究结论不一致的原因。
- **B. 核心假设构建与验证：** 基于两种效应共同作用的逻辑，提出核心假设H1：商业信用融资与破产风险之间存在非单调的U型关系。通过对中国上市公司2000-2020年的数据进行面板回归分析，并使用Utest检验，验证了该U型关系的存在。
- **C. 调节机制与深层检验：** 引入社会信任作为调节变量，提出假设H2：社会信任会弱化商业信用与破产风险之间的U型关系。通过引入交互项（TC×Trust 和 TC²×Trust）进行回归分析，证实了社会信任的平滑作用。最后，通过渠道检验（流动性渠道和融资约束渠道）进一步解释了U型关系形成的内在机制。
**原文铁证：**

> > “To investigate the relationship between trade credit financing and firm bankruptcy risk, we estimate the quadratic regression model... In the results, the coefficient of trade credit financing is negative... and the coefficient of its quadratic term is positive... These results imply that a non-monotonic U-shaped relationship exists...” (Section 4.1, p.6)
> “The coefficient of TC2×Trust is –0.530 and significant at 1% level, indicating that the U-shaped relationship flattens as social trust increases.” (Section 4.2, p.9)
> “We propose two potential channels through which trade credit financing has a non-monotonic U-shaped impact on bankruptcy risk: firm liquidity and financial constraints.” (Section 4.3, p.9)

### 3) 证据审查（Evidence Check）
**分析：** 在文献 [8] 中，证据类型主要为定量实证证据。其强度和局限如下：
- **数据类型与来源：**
    - **主要数据：** 2000-2020年中国A股上市公司财务数据，来源于CSMAR数据库，共37,276个公司-年度观测值。
    - **社会信任数据：** 省级层面社会信任指标，来源于中国综合社会调查（CGSS）。
    - **证据强度：** 样本量大、时间跨度长，增强了统计结论的可靠性。使用了多种稳健性检验（如替换变量、控制省份固定效应、系统GMM估计），并处理了双向因果等内生性问题，使结论更稳健。
    - **证据局限：** 研究样本仅限于上市公司，正如作者承认的，“most Chinese companies are not listed”，因此结论向更依赖商业信用和社会信任的非上市中小企业推广时需谨慎。社会信任数据为省级层面，可能无法完全捕捉企业层面的微观信任差异。
**原文铁证：**

> > “We rely on A-share listed companies in the Shanghai and Shenzhen stock markets of China during the period of 2000–2020 as our research sample... Our final sample consists of 37,276 firm-year observations from 3233 firms.” (Section 3.1, p.4)
> “Regional social trust information... is obtained from the Chinese General Social Survey (CGSS)...” (Section 3.1, p.4)
> “Our results are robust to alternative measures of key variables and tests for endogeneity...” (Abstract, p.1)
> “First, only listed companies are analysed in this study due to data availability. However, most Chinese companies are not listed...” (Section 5, p.13)

### 4) 逻辑断点（Logic Gap）
**分析：** 在文献 [8] 中，主要存在一个潜在的逻辑断点。研究将社会信任作为地区层面的宏观变量，来解释其对微观企业融资行为与风险关系的调节作用。虽然逻辑上成立，但其中隐含的因果链条——“地区社会信任高→企业间具体交易信任高→商业信用的U型关系被平滑”——并未被直接验证。研究未能排除其他地区层面因素（如法律环境、市场化程度）同时影响社会信任和主效应的可能性，尽管在稳健性检验中控制了省份固定效应，但仍可能存在遗漏变量问题。
**原文铁证：**

> > “...we construct a social trust indicator based on the CGSS. The province-level average score of these respondents’ choices is used to measure social trust (Trust).” (Section 3.2, p.4)
> “The results in Column (4) of Table 4... indicate that the non-monotonic U-shaped relationship between trade credit and bankruptcy risk holds. The coefficient of TC2×Trust is –0.530 and significant at 1% level, indicating that the U-shaped relationship flattens as social trust increases.” (Section 4.2, p.9)

### 5) 五句祛魅（Five-Sentence Demystification）
- **真实动机（The Motivation）：** ** 调和现有文献中关于商业信用融资究竟是降低还是增加企业破产风险的理论矛盾，寻找一个统一的解释框架。
- **实际操作（The Method）：** ** 基于2000-2020年中国A股上市公司的大样本数据，构建面板数据二次回归模型，检验商业信用与财务困境之间的U型关系，并引入省级社会信任指数作为调节变量进行实证分析。
- **核心发现（The Result）：** ** 证实了商业信用融资与财务困境之间存在显著的U型关系，适度的商业信用能降低风险，而过度的依赖则会增加风险；同时，地区社会信任水平能显著平滑这一U型曲线，即在高信任地区，过度使用商业信用带来的风险上升更为平缓。
- **隐藏局限（The Fine Print）：** ** 研究结论基于中国上市公司，可能不适用于非上市中小企业或其他制度环境迥异的国家。地区层面的社会信任指标可能无法精确反映企业间具体的双边信任水平。
- **一句话定性（The Verdict）：** ** 一项基于中国情境、首次系统性揭示商业信用与财务困境存在非线性U型关系并强调社会信任调节作用的重要实证研究。

### 6) 基于上述1)到5)核心价值总结

在文献 [8] 中，Tang 等人 (2025) 通过严谨的实证分析，为理解商业信用融资与企业财务困境之间的关系提供了全新的非线性视角，其核心价值在于成功调和了过往研究中的理论矛盾。该研究明确指出，商业信用对破产风险的影响并非单一的促进或抑制，而是一种U型的非线性关系。这一发现超越了以往仅关注线性效应的研究，证实了“流动性缓冲”效应与“风险传染”效应是同时存在且动态变化的。当企业适度使用商业信用时，能够有效缓解融资约束、补充流动性，从而降低陷入财务困境的概率；然而，一旦企业对商业信用的依赖超过某个临界点，高昂的融资成本、沉重的债务负担以及供应链风险的传染效应将占据主导，反而会显著推高其破产风险。

更重要的是，文献 [8] (Tang et al., 2025) 创新性地将社会信任这一非正式制度引入分析框架，揭示了其对U型关系的平滑调节作用。研究发现，在地区社会信任水平较高的环境中，商业信用与财务困境之间的U型曲线会变得更加平缓。这表明，高水平的信任作为一种社会资本，能够强化企业间的合作与信息共享，降低交易成本和不确定性，从而在两方面发挥作用：一方面帮助企业在适度使用阶段更有效地获取信用支持，另一方面在过度依赖阶段抑制风险的快速累积和传染，增强了整个供应链的韧性。这一发现不仅深化了对商业信用动态效应的理解，也为理解宏观社会文化如何影响微观企业财务决策与风险提供了关键证据。

此外，该研究还通过渠道检验，阐明了U型关系形成的两条核心路径——企业流动性水平和融资约束程度，为理论机制提供了实证支持。研究结论具有明确的实践指导意义：对企业而言，应制定可持续的商业信用政策，避免过度依赖；对供应商而言，需警惕过度授信带来的风险传染；对政策制定者而言，则应重视培育社会信任等非正式制度，以营造更健康的商业环境，降低系统性金融风险。尽管其结论在向非上市公司推广时需保持审慎，但文献 [8] (Tang et al., 2025) 无疑为商业信用与风险管理领域的文献库贡献了一个重要且新颖的理论模块。

### 7) 参考文献条目（GB/T 7714-2015）
[8] TANG Y, WANG B, MORO A, et al. Trade credit financing, social trust, and financial distress: Evidence from Chinese listed companies[J]. Research in International Business and Finance, 2025, 79: 103053.