            # Display a preview of the processed data
            st.subheader("Data Preview")
            
            # Create a clean dataframe for the summary table
            display_df = pd.DataFrame(processed_data)
            display_df['comments'] = display_df['comments'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
            
            st.dataframe(
                display_df[["employee", "total_available", "comments"]],
                use_container_width=True,
                hide_index=True
            )
            
            # Add an expander to view the exact shifts allocated to each person
            with st.expander("🔍 View Detailed Shift Allocations"):
                for person in processed_data:
                    st.write(f"**{person['employee']}** ({person['total_available']} shifts)")
                    st.write(person['available_shifts'])
                    st.divider()
            
            st.info("Availability data has been saved and is ready for the allocation engine.")
            
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
