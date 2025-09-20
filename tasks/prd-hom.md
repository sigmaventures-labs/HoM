# **HR Intelligence Platform \- Product Requirements Document**

## **Status: Draft**

**Product Manager:** TBD  
 **Engineer:** TBD (Junior/Intermediate)  
 **Timeline:** 1-2 weeks part-time

## **Problem Statement**

### **For HR Manager**

HR managers need a consolidated view of key HR indicators without spending hours navigating Paycom's transactional interface. They require both clear visibility into metrics and AI-powered assistance to understand and improve them. The separation between transactional operations (Paycom) and strategic analytics (this platform) is critical for effective HR management.

### **For CEO**

CEOs need a bird's-eye view of key HR indicators with confidence that:

1. HR metrics are trending in the right direction  
2. The HR function is meaningfully contributing to company strategy and performance

Unlike MaX's OEI approach, this platform focuses on the 3-5 most critical HR metrics contextually relevant to the company's current transformation stage.

## **Vision**

Create a focused analytics layer above Paycom that transforms raw HR data into strategic insights through a progressive journey from understanding what's happening to knowing what to do about it.

## **Value Proposition**

The platform provides a three-stage analytics journey:

1. **See** \- Interactive dashboard showing what matters most  
2. **Understand** \- AI-powered exploration of why metrics are trending  
3. **Act** \- Specific, prioritized recommendations for improvement

## **Target Users**

### **Primary: HR Manager/Director**

* **Journey**: Daily dashboard review → Weekly deep-dive conversations → Monthly action planning  
* **Key Need**: Transform from reactive reporting to proactive problem-solving

### **Secondary: CEO/Executive Team**

* **Journey**: Weekly dashboard glance → Monthly strategic conversations → Quarterly progress reviews  
* **Key Need**: Confidence in HR's strategic contribution

## **Core User Journey & Features**

### **Stage 1: Dashboard View (Descriptive Analytics)**

**"What's happening?"**

#### **Landing Experience**

* **No composite index** \- Display 4 critical metrics directly  
* **MVP Metrics Set**:  
  * **Headcount**: Total employees \+ % variation from previous period \+ Direct vs. Indirect breakdown  
  * **Employee Absenteeism Rate**: Percentage of unplanned absences from scheduled hours  
  * **Employee Turnover Rate**: Overall rate   
  * **Overtime**: Total hours \+ percentage of standard operating time

#### **Visual Design**

* Each metric displayed as a card (similar to MaX):  
  * Current value (large, prominent)  
  * Target value  
  * Trend indicator (↑↓→)  
  * Mini sparkline (last 12 weeks)  
  * Status indicator (green/yellow/red)  
* **Critical difference from MaX**: Instead of "View Details" and "Improvement Levers" buttons, single "Ask AI" button per metric

### **Stage 2: Conversational Exploration (Explanatory & Predictive Analytics)**

**"Why is this happening and what's likely to happen next?"**

#### **Chatbot Interface Activation**

* Clicking "Ask AI" on any metric opens conversational interface  
* Pre-populated with context: "Tell me about \[Metric Name\]"  
* AI immediately provides:  
  * Natural language explanation of current state  
  * Key drivers behind the metric  
  * Predicted trajectory (next 30/60/90 days)

#### **Ephemeral UI for Deep Dives**

During conversation, AI can dynamically generate:

* **Drill-down visualizations**: "Here's turnover broken down by department..."  
* **Correlation analysis**: "This spike correlates with overtime hours..."  
* **Cohort comparisons**: "New hires from Q1 vs Q2 performance..."  
* **What-if scenarios**: "If we improve time-to-hire by 20%, we'd see..."

#### **Conversation Capabilities**

* Natural follow-up questions  
* Cross-metric analysis ("How does turnover affect productivity?")  
* Historical pattern recognition  
* Anomaly explanation

### **Stage 3: Action Generation (Prescriptive Analytics)**

**"What should we do about it?"**

#### **Automated Action Generation**

Upon request, AI automatically generates:

* **3-5 Specific Actions** ranked by impact  
* **For each action**:  
  * Clear description  
  * Expected impact on metric  
  * Implementation difficulty (Easy/Medium/Hard)  
  * Timeline to impact  
  * First step to take

#### **Fixed UI for Action Management**

* **Action Board** (separate view):  
  * All AI-generated actions across all conversations  
  * Status tracking (Not Started/In Progress/Complete)  
  * Impact tracking (metric changes after implementation)  
  * Priority matrix (Impact vs. Effort)  
* **Playbook Library**:  
  * Detailed guides for common actions  
  * Templates and checklists  
  * Success stories from implementation

## **Technical Architecture**

### **Frontend Components**

#### **Dashboard Module (from MaX)**

* Reuse card components (90% compatible)  
* Adapt metric calculations  
* Replace button actions with "Ask AI" trigger

#### **Conversational Module (New, Reusable)**

Components:  
\- ChatInterface: Main conversation UI  
\- EphemeralChart: Dynamic visualization renderer  
\- ContextManager: Maintains conversation state  
\- ResponseFormatter: Structures AI outputs

#### **Action Module (Hybrid)**

* Reuse MaX's Improvement Levers structure (70%)  
* Add status tracking capabilities  
* Create action board view

### **Backend Services**

#### **Data Service (from MaX)**

* Metric calculation engine  
* Historical data storage  
* Trend analysis

#### **AI Orchestration Service (New)**

Responsibilities:  
\- Conversation management  
\- Context injection (metric data into prompts)  
\- Ephemeral UI generation  
\- Action generation pipeline

#### **Integration Service**

* Paycom API connector  
* Data transformation layer  
* Sync scheduler

### **AI Agent Design**

#### **Single Agent Approach: "Alex" (AI HR Analyst)**

Instead of multiple specialist agents, one comprehensive agent with three modes:

1. **Explanation Mode**: Activated when user asks about metrics

   * Analyzes trends and patterns  
   * Identifies correlations  
   * Explains in business terms  
2. **Prediction Mode**: Activated for forward-looking questions

   * Projects metric trajectories  
   * Identifies risks and opportunities  
   * Simulates intervention impacts  
3. **Prescription Mode**: Activated at conversation end

   * Generates specific actions  
   * Prioritizes based on impact/effort  
   * Provides implementation guidance

### **Data Flow**

Paycom → Daily Sync → PostgreSQL → Metric Calculation → Dashboard  
                                  ↓  
                        User Clicks "Ask AI"  
                                  ↓  
                    Conversation Context Created  
                                  ↓  
                        AI Agent Activated  
                                  ↓  
                   Ephemeral UI \+ Explanations  
                                  ↓  
                     Action Items Generated  
                                  ↓  
                      Action Board Updated

## 

## **Conversational Flow Examples**

### **Example 1: Turnover Investigation**

**User:** \[Clicks on Turnover Rate showing 18% in red\]

**Alex:** Your turnover rate is currently 18%, which is 6% above your target of 12%. Looking at the breakdown by termination reason:

* Better Opportunity: 8% (44% of all turnover)  
* Compensation: 4% (22% of all turnover)  
* Work Environment: 3% (17% of all turnover)  
* Performance: 2% (11% of all turnover)  
* Other: 1% (6% of all turnover)

The "Better Opportunity" category spiked in the last quarter, primarily in your direct labor force (Production and Warehouse).

\[Chart showing turnover by reason over 6 months\]

Additionally, your 90-day turnover is at 35%, indicating significant onboarding or hiring misalignment issues.

**User:** What's the financial impact of this?

**Alex:** Based on your average replacement costs, the excess turnover (6% above target) is costing approximately $67,000 per month:

* Recruitment costs: $12,000  
* Training/onboarding: $18,000  
* Lost productivity: $37,000

The high 90-day turnover alone accounts for $28,000 of this monthly cost.

**User:** How do I fix this?

**Alex:** Here are my top 3 recommendations:

1. **Address "Better Opportunity" Departures** \[Highest Priority\]

   * Conduct stay interviews focusing on career path concerns  
   * Implement skills development program for direct labor  
   * Create clear advancement pathways from direct to indirect roles  
   * Potential Impact: Reduce turnover by 4% in 90 days  
2. **Fix Onboarding Process** \[High Priority\]

   * Redesign first 90 days for new direct labor employees  
   * Assign mentors for all new production workers  
   * Weekly check-ins during probation period  
   * Potential Impact: Cut 90-day turnover from 35% to 20%  
3. **Review Compensation Competitiveness** \[Medium Priority\]

   * Benchmark direct labor wages against local market  
   * Consider shift differentials or skill-based pay  
   * Potential Impact: Reduce compensation-driven turnover by 2%

### **Example 2: Absenteeism Pattern Analysis**

**User:** \[Clicks on Absenteeism Rate showing 8.5% in yellow\]

**Alex:** Your absenteeism rate is 8.5%, up from 6.2% last quarter. This includes both paid sick leave and unpaid absences. Breaking it down:

* Paid sick leave: 5.5% of scheduled hours  
* Unpaid absences: 3% of scheduled hours

The pattern shows Monday/Friday absences are 40% higher than mid-week, suggesting potential engagement or burnout issues rather than genuine illness.

Departments with highest rates:

* Fabrication: 11.2% (mostly indirect labor)  
* Assembly: 9.8% (mostly direct labor)  
* Shipping: 7.1%

This correlates strongly with departments showing high overtime.

**User:** Is this related to our overtime problem?

**Alex:** Yes, there's a strong correlation. Departments with \>15% overtime show 3x higher absenteeism. Fabrication has averaged 18 hours of OT per week per employee, and their absenteeism jumped from 4% to 11.2% over the same period. This suggests fatigue-driven absences.

The estimated cost impact:

* Lost productivity from absences: $45,000/month  
* Overtime to cover absences: $22,000/month  
* Total monthly impact: $67,000

Reducing overtime could simultaneously reduce both costs.

**User:** What should I do?

**Alex:** Here are targeted recommendations:

1. **Immediate Overtime Reduction in Fabrication** \[Highest Priority\]

   * Cap weekly OT at 10 hours per employee  
   * Hire 3 additional fabricators (cost offset by OT savings)  
   * Potential Impact: Reduce absenteeism to 7% in 30 days  
2. **Implement Fatigue Management Program** \[High Priority\]

   * Mandatory rest days after 50+ hour weeks  
   * Rotate high-OT assignments among team  
   * Potential Impact: 25% reduction in Monday/Friday absences  
3. **Address Root Cause of Overtime Need** \[Medium Priority\]

   * Review production scheduling for inefficiencies  
   * Cross-train assembly workers for fabrication  
   * Potential Impact: Structural 20% reduction in OT needs

## 

## 

## **Development Roadmap**

### **Week 1 Sprint (Part-time)**

**Day 1-2: Foundation**

* Fork MaX codebase  
* Strip out manufacturing-specific elements  
* Set up Paycom integration framework  
* Define 5 core HR metrics

**Day 3: Dashboard Adaptation**

* Modify metric cards for HR KPIs  
* Implement "Ask AI" buttons  
* Create metric calculation layer  
* Test with sample data

**Day 4-5: Conversational Core**

* Build chat interface component  
* Implement AI orchestration service  
* Create ephemeral UI rendering system  
* Initial prompt engineering for "Alex"

### **Week 2 Sprint (Part-time)**

**Day 1-2: AI Enhancement**

* Refine conversation flows  
* Implement context management  
* Build action generation pipeline  
* Test explanation quality

**Day 3: Action Management**

* Create action board UI  
* Build status tracking system  
* Implement priority matrix  
* Add basic playbooks

**Day 4-5: Integration & Polish**

* Complete Paycom sync  
* End-to-end testing  
* Performance optimization  
* Deployment preparation

## **Key Design Decisions**

### **1\. No Composite Index**

Unlike MaX's OEI, showing 3-5 critical metrics directly is clearer for HR context and avoids oversimplification of complex human capital dynamics.

### **2\. Chatbot as Navigation**

Replacing MaX's "View Details" and "Improvement Levers" buttons with conversational interface reduces UI complexity while providing more flexible exploration.

### **3\. Ephemeral vs. Fixed UI**

* **Ephemeral**: Explanatory visualizations (generated as needed)  
* **Fixed**: Dashboard and action board (consistent reference points)

### **4\. Single AI Agent**

One well-trained agent with multiple modes is simpler than multiple specialists and easier to maintain consistency.

## **Success Metrics**

### **Adoption Metrics**

* Time to first "Ask AI" click: \<2 minutes  
* Conversations per user per week: \>3  
* Actions generated to actions started ratio: \>30%

### **Value Metrics**

* Reduction in report preparation time: \>50%  
* Improvement in tracked metrics: Measurable within 60 days  
* Executive dashboard views: Weekly consistency

### **Quality Metrics**

* AI explanation accuracy: \>90% (user validated)  
* Action relevance score: \>4/5  
* Conversation satisfaction: \>80%

## **Reusable Components for Software Studio**

### **Created in This Project**

1. **Conversational Navigation Pattern**: "Ask AI" as UI simplification strategy  
2. **Ephemeral UI System**: Dynamic visualization during conversations  
3. **Action Generation Framework**: Prescriptive analytics pipeline  
4. **Paycom Connector**: Reusable for future HR products

### **Leveraged from MaX**

1. **Dashboard Components**: 90% reuse  
2. **Metric Calculation Engine**: 70% reuse  
3. **Admin Interface**: 95% reuse  
4. **Data Service Layer**: 80% reuse

## **MVP Release Criteria**

* \[ \] Dashboard displays 5 defined HR metrics with real Paycom data  
* \[ \] "Ask AI" triggers conversation for each metric  
* \[ \] AI provides meaningful explanations for metric trends  
* \[ \] Ephemeral visualizations render during conversations  
* \[ \] Each conversation generates 3+ relevant actions  
* \[ \] Action board tracks implementation status  
* \[ \] Response time \<3 seconds for dashboard, \<5 seconds for AI  
* \[ \] Successfully processes 1 week of historical data

## **Risk Mitigation**

### **Technical Risks**

* **Paycom API Limitations**: Pre-build CSV upload alternative  
* **AI Response Quality**: Extensive prompt testing with HR-specific examples  
* **Ephemeral UI Complexity**: Start with simple chart types, expand later

### **Adoption Risks**

* **Chatbot Skepticism**: Make first interaction incredibly valuable  
* **Action Overload**: Limit to 5 actions visible at once, archive completed  
* **Metric Confusion**: Include glossary/definitions in dashboard hover states

## **Post-MVP Enhancements**

**Quick Wins (Week 3-4)**

* Email digest of weekly metrics  
* Mobile-responsive design  
* Export to PowerPoint for board meetings

**Phase 2 (Month 2\)**

* Predictive alerts ("3 employees at flight risk")  
* Benchmark comparisons (industry/size)  
* Integration with more Paycom modules

**Phase 3 (Month 3+)**

* Multi-company rollout capabilities  
* Advanced ML models for prediction  
* Integration with other HR tools

