# Who should finance the supply chain_ Impact of accounts receivable mortgage on supply chain decision 逆向工程分析

### 0) 文献身份锚点
- **文献编号**：[9]
- **锁定引用**：Cheng et al. (2023)
- **核心标签**：`应收账款抵押`、`资本约束供应链`、`银行信贷政策`

### 1) 核心假设（Premise）
**分析：** 在文献 [9] 中，Cheng et al. (2023) 的研究从零售商和制造商均面临资本约束，且银行会根据企业初始运营能力（初始资本）设定差异化利率的前提出发。其隐藏假设是，银行的信贷政策（利率）是内生的，取决于供应链成员的订单决策和破产风险，并且存在一个完美的资本市场（无破产成本）。

**原文铁证：**

> > **分析：** “We consider a supply chain consisting of a capital-constrained retailer (he), a capital-constrained manufacturer (she), and a bank (it).” (Section 3)
> **分析：** “The accounts receivable mortgage contract includes a multi-discount interest rate (risk-free interest rate, general loan interest rate for SMEs, and risk compensation interest rate) according to the retailer’s order quantity contract, retailer’s initial capital (BR), and manufacturer’s initial capital (BM).” (Section 3)
> **隐藏假设：** “(ii) The capital market is perfect, i.e., there are no bankruptcy costs, taxes, or transaction costs; retailer and manufacturer are risk-neutral and maximize their own profit; ...” (Section 3.1, Assumption ii)

### 2) 推演路径（Inference）
**分析：** 在文献 [9] 中，Cheng et al. (2023) 的推演路径从银行基于企业初始资本设定差异化利率开始，最终得出不同融资方式下的最优决策和供应链效率比较。

**原文铁证：**

> > - **A（起点：银行差异化信贷政策）**：“The bank would give different types of interest rates (risk-free rate, general rate, and risk compensation interest rate) based on their risk evaluation on the qualification of the players.” (Section 2)
> - **B（构建博弈模型）**：“To answer the above question, we establish a Stackelberg game that involves three parties: a capital-constrained retailer, a capital-constrained manufacturer, and a bank.” (Section 1)
> - **C（推演至均衡决策）**：“We identify optimal decisions in different situations...” (Abstract)
> - **D（核心发现：供应链效率与融资选择）**：“...finding that supply chain efficiency is better attained using bank short-term loans... Specifically, we find that the optimal sourcing choices depend on the ratio of the share of the manufacturer with the share of the retailer (RMR).” (Abstract)

### 3) 证据审查（Evidence Check）
**分析：** 在文献 [9] 中，Cheng et al. (2023) 提供了两类证据：一是通过数理模型推导得出的理论证据，二是通过面板数据回归得出的实证证据。理论模型的局限在于其严格假设，实证证据的局限在于数据来源和代理变量的选择。

**原文铁证：**

> > - **证据类型 1：数理模型推导**
>   - **原文铁证：** “Proposition 1. ...the optimal order quantity q∗ T satisfies the first-order optimality condition...” (Section 4.1)
>   - **分析：** 此为理论证据，通过严格的数学推导得出。
> - **证据类型 2：实证检验**
>   - **原文铁证：** “Based on 17 industries of Chinese firms’ data, we consider the panel regression to confirm the results of (i) and (ii).” (Section 6)
>   - **分析：** 此为实证证据，使用中国企业的面板数据对理论假说进行检验。
> - **证据强度与局限**
>   - **原文铁证（局限）：** “We use the cash ratio to describe firm solvency, such as low solvency, moderate solvency and high solvency.” (Section 6.1)
>   - **分析：** 实证中采用“现金比率”作为企业偿付能力的代理变量，这可能无法完全反映理论模型中的“初始运营能力”。

### 4) 逻辑断点（Logic Gap）
**分析：** 在文献 [9] 中，Cheng et al. (2023) 存在一个逻辑断点：将理论模型中基于“初始资本”区分的偿付能力（高、中、低），在实证部分直接等同于基于“现金比率”或“速动比率”划分的企业类型。虽然具有合理性，但“初始资本”在模型中是一个静态的、用于决定利率的参数，而“现金比率”是动态的财务指标，两者并非完全等同，这种从理论构念到实证代理变量的跳跃可能引入测量误差。

**原文铁证：**

> > **分析（理论定义）：** “The qualifications of manufacturers and retailers would be evaluated by their initial capital.” (Section 3)
> **分析（实证定义）：** “We use the cash ratio to describe firm solvency, such as low solvency, moderate solvency and high solvency.” (Section 6.1)
> **逻辑跳跃：** 理论中的“初始资本”直接过渡为实证中的“现金比率”，两者虽有联系，但概念边界不完全一致，存在外推过度的风险。

### 5) 五句祛魅（Five-Sentence Demystification）
- **真实动机（The Motivation）：** ** 探究在零售商和制造商都缺钱的情况下，基于应收账款抵押的银行贷款如何影响供应链决策，特别是银行对不同信用等级企业实行差异化利率会产生什么后果。
- **实际操作（The Method）：** ** 构建了一个银行、制造商和零售商的三方斯坦克尔伯格博弈模型，根据企业的初始资本和订单量将银行利率分为无风险利率、中小企业一般利率和风险补偿利率三种，并用中国企业的面板数据进行了实证检验。
- **核心发现（The Result）：** ** 理论表明，供应链效率在零售商直接获得银行贷款时更高；融资方式的选择取决于制造商与零售商的资本份额之比（RMR），RMR低时用贸易信贷，反之用银行信贷；且偿付能力高的企业订货量更大。
- **隐藏局限（The Fine Print）：** ** 模型假设资本市场完美（无破产成本），且企业风险中性，这简化了现实世界的复杂性。实证部分用“现金比率”来代理理论模型中的“初始资本”和“偿付能力”，两者并非完全等同。
- **一句话定性（The Verdict）：** ** 一篇通过引入银行差异化利率来深化运营-金融交叉领域研究，并用中国数据验证了“高偿付能力企业订货更多”和“银行信贷更优”的理论文章。

### 6) 基于上述1)到5)核心价值总结

在文献 [9] 中，Cheng et al. (2023) 深入探讨了应收账款抵押融资在资本约束供应链中的作用机理，其核心价值在于打破了以往研究将银行视为风险中性的简化处理，构建了一个更为贴近现实的模型。该模型的核心创新在于，银行会根据供应链成员的初始运营能力（由初始资本衡量）和订单量，提供包含无风险利率、中小企业一般利率和风险补偿利率在内的差异化信贷政策。通过这一理论框架，Cheng et al. (2023) 揭示了银行风险偏好如何内生于供应链的运营决策，并最终影响零售商和制造商的订货量与定价策略 [9]。

研究的一个重要理论贡献是明确了供应链融资渠道选择的边界条件。Cheng et al. (2023) 发现，最优的融资方式并非一成不变，而是取决于制造商与零售商的资本份额之比（RMR）。当该比率较低时，贸易信贷是更优的选择；反之，当该比率较高时，资本约束的供应链应选择银行信贷以实现更优的效率。此外，研究还发现，无论采用何种融资方式，具有较高偿付能力的企业总是倾向于订购更多商品，这挑战了“资本越多越保守”的简单直觉，揭示了高风险偏好与高运营能力并存的企业行为模式 [9]。

除了理论模型的构建，Cheng et al. (2023) 的另一大贡献在于提供了来自中国的实证证据。他们利用中国上市公司17个行业的面板数据，通过固定效应模型检验了理论假说。实证结果有力地支持了理论发现：企业的偿付能力（以现金比率衡量）与其订货量（通过应付账款变化体现）正相关；同时，对于偿付能力较高的企业，银行短期贷款对其边际利润的影响比贸易信贷更为显著，这表明当银行信贷可得时，它确实是资本约束零售商的更优选择。这一结论不仅验证了模型的可靠性，也为理解中国企业的融资行为提供了新的视角 [9]。

综上所述，Cheng et al. (2023) 的研究通过整合银行差异化风险偏好，极大地丰富和深化了运营与金融交叉领域的文献。其不仅从理论上剖析了应收账款抵押合同下供应链成员的互动机制，还通过实证分析增强了结论的现实解释力，为管理者理解不同信贷政策下的供应链决策提供了清晰的洞见，即提升企业自身的运营能力和偿付水平，并在条件允许时优先争取银行信贷，是提升供应链效率和利润的有效途径 [9]。

### 7) 参考文献条目（GB/T 7714-2015）
[9] CHENG Y, WEN F, WANG Y, et al. Who should finance the supply chain? Impact of accounts receivable mortgage on supply chain decision[J]. International Journal of Production Economics, 2023, 261: 108874.