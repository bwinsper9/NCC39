
import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile

st.set_page_config(page_title="Catering Companion", layout="centered", page_icon="🍴")
st.markdown("""
<style>
body {
    background-color: #f8f9fa;
    font-family: 'Segoe UI', sans-serif;
}
section.main > div {
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

df = pd.read_csv("master_recipe_template.csv")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    num_guests_input = st.text_input("Number of guests:")
    try:
        num_guests = int(num_guests_input)
    except:
        num_guests = None
    selected_recipes = st.multiselect("Select recipes:", options=df["RecipeName"].unique())

if num_guests is not None and selected_recipes:
    st.markdown("---")
    filtered_df = df[df["RecipeName"].isin(selected_recipes)].copy()

    if "checked_ingredients" not in st.session_state:
        st.session_state.checked_ingredients = set()

    scaled_ingredients = []
    for recipe in selected_recipes:
        recipe_df = filtered_df[filtered_df["RecipeName"] == recipe].copy()
        base_servings = recipe_df["BaseServings"].iloc[0]
        factor = num_guests / base_servings
        recipe_df["Quantity"] = pd.to_numeric(recipe_df["Quantity"], errors="coerce").fillna(0)
        recipe_df["ScaledQuantity"] = recipe_df["Quantity"] * factor
        scaled_ingredients.append(recipe_df)
    full_df = pd.concat(scaled_ingredients)

    combined = full_df.groupby(["Ingredient", "Unit", "Category"], as_index=False).agg({"ScaledQuantity": "sum"})

    final_combined = combined[~combined.apply(lambda x: (x["Ingredient"], x["Unit"]) in st.session_state.checked_ingredients, axis=1)]

    def generate_shopping_list_pdf(df):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Shopping List", ln=True, align="C")
        pdf.ln(10)
        for _, row in df.iterrows():
            line = f"- {round(row['ScaledQuantity'], 2)} {row['Unit']} {row['Ingredient']}"
            pdf.cell(200, 10, txt=line, ln=True)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(temp_file.name)
        return temp_file

    def generate_recipe_guides(recipes_df):
        pdf = FPDF()
        pdf.set_font("Arial", size=12)
        for recipe in selected_recipes:
            section = recipes_df[recipes_df["RecipeName"] == recipe].copy()
            if not section.empty:
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(200, 10, txt=f"{recipe} - Recipe Guide", ln=True, align="C")
                pdf.ln(8)
                base_servings = section["BaseServings"].iloc[0]
                factor = num_guests / base_servings
                pdf.set_font("Arial", "B", 12)
                pdf.cell(200, 10, txt="Ingredients:", ln=True)
                pdf.set_font("Arial", size=12)
                for _, row in section.iterrows():
                    scaled_qty = round(row["Quantity"] * factor, 2)
                    line = f"- {scaled_qty} {row['Unit']} {row['Ingredient']}"
                    pdf.cell(200, 10, txt=line, ln=True)
                method_rows = section.dropna(subset=["Method"])
                if not method_rows.empty:
                    pdf.ln(6)
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(200, 10, txt="Method:", ln=True)
                    pdf.set_font("Arial", size=12)
                    for _, row in method_rows.iterrows():
                        pdf.multi_cell(0, 10, f"{row['Ingredient']}: {row['Method']}")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(temp_file.name)
        return temp_file

    shopping_pdf = generate_shopping_list_pdf(final_combined)
    recipe_pdf = generate_recipe_guides(filtered_df)

    f1 = open(shopping_pdf.name, "rb")
    f2 = open(recipe_pdf.name, "rb")

    with st.sidebar:
        st.markdown("### 📥 Download PDFs")
        st.download_button("Download Shopping List PDF", data=f1, file_name="shopping_list.pdf", mime="application/pdf", key="shopping_pdf")
        st.download_button("Download Recipe Guides PDF", data=f2, file_name="recipe_guides.pdf", mime="application/pdf", key="recipe_pdf")

    st.markdown("### 🧾 Shopping List Preview")
    with st.expander("Tap to check off ingredients", expanded=True):
        for idx, row in combined.iterrows():
            label = f"{round(row['ScaledQuantity'], 2)} {row['Unit']} {row['Ingredient']}"
            key = f"checkbox_{row['Ingredient']}_{row['Unit']}"
            if st.checkbox(label, key=key):
                st.session_state.checked_ingredients.add((row["Ingredient"], row["Unit"]))
            else:
                st.session_state.checked_ingredients.discard((row["Ingredient"], row["Unit"]))

    st.markdown("---")
    st.markdown("### ✅ Final Shopping List")
    for category, group in final_combined.groupby("Category"):
        with st.expander(category, expanded=False):
            for _, row in group.iterrows():
                st.write(f"- {round(row['ScaledQuantity'], 2)} {row['Unit']} {row['Ingredient']}")
