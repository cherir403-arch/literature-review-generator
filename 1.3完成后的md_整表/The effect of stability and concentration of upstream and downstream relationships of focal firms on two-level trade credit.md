# The effect of stability and concentration of upstream and downstream relationships of focal firms on two-level trade credit 逆向工程分析

### 0) 文献身份锚点
- **文献编号**：[6]
- **锁定引用**：Zhang et al. (2024)
- **核心标签**：{买方-供应商关系}、{稳定性}、{集中度}、{两级商业信用}

### 1) 核心假设（Premise）
**分析：** 在文献 [6] 中，Zhang et al. (2024) 的研究从以下前提出发：现有文献主要探讨了买方-供应商关系的单一特征（如稳定性或集中度）对企业商业信用的影响，但未将上下游关系的这两个维度同时纳入考量，也未能区分焦点企业获得（来自上游）和提供（给下游）的两级商业信用。其隐藏假设是，上游（供应商）和下游（客户）关系的稳定性与集中度，对焦点企业的两级商业信用具有不对称的、甚至是相反的影响机制。

**原文铁证：**

> > **原文证据1：** “Previous studies have focused on the impact of a single characteristic of the buyer–supplier relationships on the trade credit of focal firms.” (Introduction, p.1)
> **原文证据2：** “In this study, we investigated 973 A-share listed firms in China from 2012 to 2021 and adopted ordinary least squares regression to analyze the effects of stability and concentration in both upstream and downstream relationships on two-level trade credit.” (Abstract, p.1)
> **原文证据3：** “To figure out the question, we explore the focal firms’ two-level trade credit from the perspective of characteristics of the UD relationship, which include stability and concentration.” (Introduction, p.2)

### 2) 推演路径（Inference）
**分析：** 在文献 [6] 中，Zhang et al. (2024) 的推演路径从核心问题出发，分解为四个子问题，逐步推导至最终结论。

**原文铁证：**

> > **A→B→C 推演路径：**
> - **A (起点：研究问题):** 上游和下游关系的稳定性与集中度如何影响焦点企业的两级商业信用？
> - **B1 (分解问题1 - 上游):** “First, we delve into the upstream relationship as the subject of our initial research question: what impact do supplier stability and concentration have on trade credit received by focal firms?” (Section 1, p.2)
> - **B2 (分解问题2 - 下游):** “Second, we address the research issue by focusing on the downstream: how do customer stability and concentration affect trade credit provided by focal firms?” (Section 1, p.2)
> - **B3 (分解问题3 - 调节效应):** “Consequently, our third research query delves into elucidating the significance of focal firms’ market power in shaping the influence of stability and concentration of UD relationships on two-level trade credit.” (Section 1, p.2)
> - **B4 (分解问题4 - 信用成本):** “Last, Given that trade credit models differ in terms of financing costs. Thus, we put forward our last research question: what impact does the stability and concentration of UD relationships have on the focal firms’ trade credit models?” (Section 1, p.2)
> - **C (终点：结论):** 研究发现供应商稳定性正向影响、集中度负向影响焦点企业获得的商业信用；客户稳定性与集中度均正向影响焦点企业提供的商业信用；焦点企业的市场权力对上述关系具有调节作用；高供应商集中度不利于焦点企业选择低成本的商业信用模式，而客户稳定性则有利。

### 3) 证据审查（Evidence Check）
**分析：** 在文献 [6] 中，Zhang et al. (2024) 采用的证据类型为二手面板数据，并通过多种计量方法进行检验。证据强度较高，但仍存在样本选择和数据精确性方面的局限。

**原文铁证：**

> > **证据类型：** “We selected the data of A-share listed firms from 2012 to 2021, and the major data source is CSMAR.” (Section 3.1, p.4)
> - **数据源：** 中国A股上市公司，数据来自CSMAR数据库。
> - **样本量：** “Our final datasets consisted of 973 A-share listed firms observed from 2012 to 2021, including 3137 upstream and 3655 downstream observations.” (Section 1, p.2)

> **证据强度：**
> - **多元回归分析：** “adopted ordinary least squares regression to analyze the effects...” (Abstract, p.1)
> - **稳健性检验：** 研究进行了包括Heckman两阶段模型、滞后效应、更换变量衡量方式、公司层面聚类等多种稳健性检验。 “Therefore, we used Heckman’s two-stage to mitigate the potential impact of this issue on the conclusions...” (Section 4.3.1, p.7); “we further changed the measurements of independent variables...” (Section 4.3.4, p.8); “we re-test our hypotheses by using the robust error model, which is clustered at the firm level.” (Section 4.3.5, p.8)
> - **证据局限：**
>   - **样本选择局限：** “Given that the assessment of stability necessitated a direct correlation of supplier and customer names, this resulted in a more restricted dataset for our study.” (Section 3.1, p.4) 即因为需要匹配供应商和客户名称，导致有效样本量减少。
>   - **情境局限：** “Finally, the context of our data is limited to Chinese-listed firms...” (Section 6.4, p.16) 结论向其他国家推广需谨慎。

### 4) 逻辑断点（Logic Gap）
**分析：** 在文献 [6] 中，Zhang et al. (2024) 的推演存在一个主要的逻辑断点。作者虽然证实了稳定性和集中度与两级商业信用之间的显著关系，但在从“相关性”跳跃到“因果性”的解释上，主要依赖理论（如资源依赖理论、BS关系理论）进行推论，未能完全排除遗漏变量或反向因果的内生性问题。尽管做了Heckman和滞后检验，但无法完全证明其识别的因果关系是唯一的解释。

**原文铁证：**

> > **关于因果解释的依赖：**
> “According to goal interdependence theory, stable customers also strengthen their interdependence with focal firms... Thus, a community of interest is more likely to form among focal firms and stable customers.” (Section 2.4, p.3)
> “From a competitive perspective. When highly concentrated, customers tend to possess greater bargaining power and financial control over the focal firms... Thus, major customers may control focal firms and compel them to make concessions...” (Section 2.4, p.3)
> **关于内生性的处理与局限：**
> “to mitigate the potential endogeneity problem arising from reverse causality, current period data... while SUS, SUC, CUS and CUC for the previous year... was included in our study.” (Section 4.3.2, p.7) 这种做法能缓解但无法完全消除反向因果问题。
> 作者在局限性部分也未直接讨论因果识别的根本挑战，而是指出了未来研究可探索机制。 “the influence mechanism was not further examined in this study.” (Section 6.4, p.16)

### 5) 五句祛魅（Five-Sentence Demystification）
- **真实动机（The Motivation）：** ** 打破现有研究仅从单一维度（稳定性或集中度）考察供应链关系对商业信用影响的局限，首次从上游和下游双向、以及关系特征的两个核心维度，系统性地揭示其对焦点企业“两级商业信用”的不对称影响。
- **实际操作（The Method）：** ** 基于2012-2021年中国A股973家上市公司的供应链数据，运用多元线性回归模型，分别检验了供应商/客户的稳定性与集中度对焦点企业获得/提供商业信用的影响，并进一步考察了市场权力的调节作用和不同商业信用模式的成本差异。
- **核心发现（The Result）：** ** 研究发现，供应商稳定性促进焦点企业获得商业信用，而供应商集中度则抑制这一过程；相反，客户的稳定性和集中度都能促进焦点企业向其提供更多商业信用。此外，焦点企业的市场权力能削弱供应商端的影响，但会强化客户集中度对提供信用的正向作用。
- **隐藏局限（The Fine Print）：** ** 研究样本仅限于中国上市公司，且因需要追踪具体交易对象名称而导致样本量进一步缩减，结论向其他制度环境或非上市企业的推广需谨慎。同时，研究未能完全打开从关系特征到信用行为的“黑箱”，其间的中介机制有待未来探索。
- **一句话定性（The Verdict）：** ** 这是一项从“双边关系”扩展到“三链条视角”、细致区分了供应链上下游关系不同维度对“两级商业信用”不对称影响的实证研究，为供应链金融管理提供了新的洞察。

### 6) 基于上述1)到5)核心价值总结

在文献 [6] 中，Zhang et al. (2024) 的研究立足于供应链金融领域，针对现有研究多聚焦于买方-供应商关系的单一特征这一缺口，构建了一个更为全面的分析框架。该研究的核心价值在于，它首次将供应链上下游关系的“稳定性”与“集中度”这两个核心维度，与焦点企业的“两级商业信用”（即从供应商处获得的信用和向客户提供的信用）联系起来，系统性地揭示了两者之间存在的非对称影响机制。

研究发现，焦点企业与其上游供应商的关系特征对其获得的商业信用具有显著且相反的影响。具体而言，与供应商建立长期稳定的合作关系，有助于焦点企业获得更多的商业信用，这被解释为基于信任和长期合作导向的互惠行为。相反，如果焦点企业的采购过度集中于少数几家主要供应商，即供应商集中度过高，则会因依赖关系失衡和供应商议价能力增强而对其获得商业信用产生负面影响。这一发现清晰地表明，在管理上游关系时，追求“稳定”比追求“集中”更有利于焦点企业的融资。

从下游关系的角度看，研究结论呈现出截然不同的模式。无论是与下游客户关系的稳定性还是集中度，均对焦点企业向客户提供的商业信用产生正向影响。一方面，稳定的客户关系意味着更强的相互依赖和共同利益，促使焦点企业愿意提供更多信用以维系关系。另一方面，高客户集中度虽然可能带来客户议价能力的提升，但也代表着稳定的销售收入和关系专用性投资，这使得焦点企业为了留住大客户而倾向于提供更多商业信用。因此，在处理下游关系时，无论是“稳定”还是“集中”，都构成了焦点企业提供信用的动机。

此外，Zhang et al. (2024) 的研究还进一步揭示了情境因素的重要性，发现焦点企业自身的市场权力在上述关系中扮演着关键的调节角色。市场权力较强的焦点企业，能够在一定程度上抵御供应商端的不利影响，即削弱供应商稳定性对其获得信用的正向作用，同时也削弱供应商集中度对其获得信用的负向作用。这体现了强势买方在供应链中的议价能力。而在下游，市场权力则会放大客户集中度对焦点企业提供信用的正向影响，表明拥有市场支配地位的焦点企业更有能力和意愿通过提供商业信用来巩固与大客户的关系。最后，通过对不同商业信用模式成本的分析，研究还指出，过高的供应商集中度会使焦点企业不得不选择成本更高的信用模式，而稳定的客户关系则为其选择低成本模式创造了条件。

综上所述，文献 [6] 的理论贡献在于，它超越了以往对供应链关系的单一维度分析，通过整合稳定性与集中度、上游与下游，构建了一个更为立体和动态的视角来理解商业信用的决定因素。它不仅丰富了供应链金融和买方-供应商关系理论，也为企业管理者提供了清晰的实践指导：即应致力于与供应商建立稳定而非过度集中的关系，同时积极发展与稳定和重要客户的合作，并善用自身的市场权力来优化供应链中的资金流管理 [6]。

### 7) 参考文献条目（GB/T 7714-2015）
Zhang J, Mo H, Hu Z, et al. The effect of stability and concentration of upstream and downstream relationships of focal firms on two-level trade credit[J]. International Journal of Production Economics, 2024, 270: 109173.