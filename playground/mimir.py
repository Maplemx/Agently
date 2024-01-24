import Agently
# Mimir is a figure in Norse mythology, renowned for his knowledge and wisdom
# ask a question for different level of complexity, try it

agent_factory = Agently.AgentFactory()

level_dict = {"0": "Child", "1": "Teen", "2": "Adult", "3": "Expert"}

user_chosen_label_index = None
while user_chosen_label_index not in level_dict:
    user_chosen_label_index = input("[0]: Child\n[1]: Teen\n[2]: Adult\n[3]: Expert")

chosen_label = level_dict[user_chosen_label_index]

agent_factory.set_settings("current_model", "Google") \
    .set_settings("model.Google.auth", {"api_key": "API_KEY"})

# main function
agent = agent_factory.create_agent() \
    .set_role("the student knowledge level", chosen_label)

if chosen_label == "Child":
    agent.set_role("role", "you are an elementary teacher") \
        .set_role("rules of actions", "First, it is necessary to determine the intention of the user input according to the {intention determination rules}, and then select the applicable according to the intention determination result to reply.") \
        .set_role("intent determination rules", "answer the question with something that children can easily find in daily life, something in school, some scenario with their parents, something with going to the shop, a restaurant, common activities that children do or do with their parents ") \
        .toggle_component("Search", True)

elif chosen_label == "Teen":
    agent.set_role("role", "you are a Middle School teacher") \
        .set_role("rules of actions", "First, it is necessary to determine the intention of the user input according to the {intention determination rules}, and then select the applicable according to the intention determination result to reply.") \
        .set_role("intent determination rules", "answer the question with something that an average teen of 15 or 14 years could understand; at this age, teens have already completed elementary school knowledge") \
        .toggle_component("Search", True)

elif chosen_label == "Adult":
    agent.set_role("role", "you are an last year of High School teacher") \
        .set_role("rules of actions", "First, it is necessary to determine the intention of the user input according to the {intention determination rules}, and then select the applicable according to the intention determination result to reply.") \
        .set_role("intent determination rules", "answer the question with something that an adult, perhaps not an expert in the field, could understand; add more complexity than, for example, explaining something for a teenager or a child. Be careful not to add too much complexity to the answer.") \
        .toggle_component("Search", True)

elif chosen_label == "Expert":
    agent.set_role("role", "you are an Ph.D in the closest field") \
        .set_role("rules of actions", "First, it is necessary to determine the intention of the user input according to the {intention determination rules}, and then select the applicable according to the intention determination result to reply.") \
        .set_role("intent determination rules", "answer the question with an expert with five years of experience in the closest field possible. For example, if the question asks something related to electricity, the closest field is an Electric Engineer. Another example, if it's related to planes or airships, it's Aerospace engineering. The last one, if it's related to History, the closest field is a Ph.D. in History.") \
        .toggle_component("Search", True)

my_input = input("[Question]: ")
reply = agent.input(my_input) \
    .instruct(f"try to answer the question for the user as their knowledge level as {chosen_label}") \
    .start()

print(reply)
